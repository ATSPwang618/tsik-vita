//! Bounded immutable text segments. Stable prefixes survive typewriter reveals;
//! changing tails, backgrounds and cursors retain their original UI order.
//! Keys retain every shader input, including per-glyph alpha and atlas versions.
use std::sync::{Arc, Weak};

use knife_perf::{Gauge, Metric, Scope, memory_budget};
#[cfg(not(test))]
use knife_render::{Blend, CANVAS_H, CANVAS_W, CommandEncoder, GpuTexture, Quad,
    RenderTarget, Renderer, Shade};
#[cfg(test)]
use crate::vita::{Blend, CANVAS_H, CANVAS_W, CommandEncoder, GpuTexture, Quad,
    RenderTarget, Renderer, Shade};

const MIN_GLYPHS: usize = 8;
const MAX_GLYPHS: usize = 1024;
const MAX_OBSERVATIONS: usize = MAX_GLYPHS / MIN_GLYPHS;
const MAX_BUILDS_PER_FRAME: usize = 2;
const IDLE_FRAMES: u64 = 600;

#[derive(Clone, PartialEq, Eq)]
struct Key(Arc<[u64]>);

struct Entry {
    key: Key,
    // Weak references prevent a freed atlas' native pointer being recycled into
    // a false key hit, without retaining old font pages in GPU memory.
    sources: Vec<Weak<GpuTexture>>,
    target: RenderTarget,
    bytes: usize,
    source_draws: usize,
    last_used: u64,
    promoted: bool,
}

#[derive(Default)]
pub(super) struct Pool {
    entries: Vec<Entry>,
    previous: Vec<Key>,
    observed: Vec<Key>,
    epoch: u64,
    bytes: usize,
    key_scratch: Vec<u64>,
    builds: usize,
}

impl Pool {
    pub fn begin_frame(&mut self) {
        self.epoch = self.epoch.wrapping_add(1).max(1);
        // Reuse both observation vectors. Repeated/cache-hit keys share their
        // immutable words instead of allocating/copying every glyph's key.
        std::mem::swap(&mut self.previous, &mut self.observed);
        self.observed.clear();
        self.builds = 0;
        let epoch = self.epoch;
        self.remove_where(|entry| epoch.saturating_sub(entry.last_used) > IDLE_FRAMES
            || entry.sources.iter().any(|source| source.strong_count() == 0));
    }

    pub fn bytes(&self) -> usize { self.bytes }

    /// A resource barrier may surrender even the most recent cached output.
    /// Recorded commands hold independent strong texture references; native
    /// retirement supplies the fence after their last reader completes.
    pub fn release_for_images(&mut self)->usize {
        let bytes=self.bytes;
        while !self.entries.is_empty() {self.remove(self.entries.len()-1);}
        self.previous.clear();self.observed.clear();
        bytes
    }

    /// Current-frame readers stay pinned. Native texture retirement supplies the
    /// GPU completion fence after the last recorded command releases its handle.
    pub fn trim(&mut self, keep_bytes: usize) {
        while self.bytes > keep_bytes {
            let victim = self.entries.iter().enumerate()
                .filter(|(_, entry)| entry.last_used != self.epoch)
                .min_by_key(|(_, entry)| entry.last_used).map(|(index, _)| index);
            let Some(victim) = victim else { break };
            self.remove(victim);
        }
        if keep_bytes == 0 {
            self.previous.clear();
            self.observed.clear();
        }
    }

    fn remove_where(&mut self, mut matches: impl FnMut(&Entry) -> bool) {
        let mut index = 0;
        while index < self.entries.len() {
            if matches(&self.entries[index]) && self.entries[index].last_used != self.epoch {
                self.remove(index);
            } else { index += 1; }
        }
    }

    fn take(&mut self, index: usize) -> Entry {
        let entry = self.entries.swap_remove(index);
        self.bytes -= entry.bytes;
        knife_perf::add(Metric::TextCacheEvict, entry.bytes as u64, 1);
        self.gauges();
        entry
    }
    fn remove(&mut self, index: usize) { drop(self.take(index)); }

    fn gauges(&self) {
        knife_perf::gauge_set(Gauge::TextCacheBytes, self.bytes as u64);
        knife_perf::gauge_set(Gauge::TextCacheEntries, self.entries.len() as u64);
    }

    /// Typing retains immutable eight-glyph prefixes. Once the caller confirms
    /// completion, a repeated exact whole-run key promotes the run into one
    /// surface, including its short tail. Per-glyph alpha remains baked exactly.
    pub fn draw_ui(&mut self, r: &mut Renderer, enc: &mut CommandEncoder,
        canvas: &RenderTarget, quads: &[Quad], finished: bool) {
        let mut begin = 0;
        while begin < quads.len() {
            let text = eligible(&quads[begin]);
            let mut end = begin + 1;
            while end < quads.len() && eligible(&quads[end]) == text { end += 1; }
            let run = &quads[begin..end];
            if !text || run.len() > MAX_GLYPHS {
                if text { knife_perf::add(Metric::TextCacheDirectGlyphs, 0, run.len() as u64); }
                r.draw(enc, canvas, None, run);
            } else if finished && self.draw_run(r, enc, canvas, run, true) {
                // Keep non-text boundaries intact even when the full finished
                // paragraph/page becomes one composite.
            } else {
                // Canonical boundaries never move when more glyphs appear.
                // An incomplete tail is direct: brief pauses during typing do
                // not create one target for every newly revealed character.
                let mut line_begin = 0;
                while line_begin < run.len() {
                    let mut line_end = line_begin + 1;
                    while line_end < run.len() && same_line(&run[line_end - 1], &run[line_end]) {
                        line_end += 1;
                    }
                    for segment in run[line_begin..line_end].chunks(MIN_GLYPHS) {
                        if segment.len() < MIN_GLYPHS || !self.draw_run(r, enc, canvas, segment, false) {
                            knife_perf::add(Metric::TextCacheDirectGlyphs, 0, segment.len() as u64);
                            r.draw(enc, canvas, None, segment);
                        }
                    }
                    line_begin = line_end;
                }
            }
            begin = end;
        }
    }

    fn draw_run(&mut self, r: &mut Renderer, enc: &mut CommandEncoder,
        canvas: &RenderTarget, quads: &[Quad], promoted: bool) -> bool {
        if self.observed.len() >= MAX_OBSERVATIONS {
            return false;
        }
        let Some(rect) = bounds(quads) else { return false };
        self.key_scratch.clear();
        self.key_scratch.extend([quads.len() as u64, rect[2].to_bits() as u64, rect[3].to_bits() as u64]);
        for quad in quads {
            append_key(&mut self.key_scratch, quad, rect);
        }
        // Lookup compares exact words. A hash alone cannot establish a hit.
        let key = self.previous.iter().chain(self.entries.iter().map(|entry| &entry.key))
            .find(|key| key.0.as_ref() == self.key_scratch.as_slice()).cloned()
            .unwrap_or_else(|| Key(Arc::from(self.key_scratch.as_slice())));
        if self.previous.get(self.observed.len()).is_some_and(|previous| previous != &key) {
            knife_perf::add(Metric::TextCacheInvalidate, 0, quads.len() as u64);
        }
        self.observed.push(key.clone());
        if let Some(entry) = self.entries.iter_mut().find(|entry| entry.key == key
            && entry.sources.iter().all(|source| source.strong_count() != 0)) {
            entry.last_used = self.epoch;
            entry.promoted |= promoted;
            // The key normalizes only an integer physical-pixel translation.
            // Scroll the cached result using this frame's rect, with unchanged
            // subpixel raster phase and unchanged per-glyph coverage.
            if r.try_composite_text_cache(enc, canvas, &entry.target, rect).is_ok() {
                knife_perf::add(Metric::TextCacheHit, entry.bytes as u64, quads.len() as u64);
                knife_perf::add(Metric::TextCacheSavedDraws, 0, entry.source_draws.saturating_sub(1) as u64);
                return true;
            }
            knife_perf::add(Metric::TextCacheFallback, 0, 1);
            return false;
        }
        knife_perf::add(Metric::TextCacheMiss, 0, quads.len() as u64);
        // During typing/fades/wobbles retain the original direct path. Building
        // only after a repeated signature avoids a render target for every glyph.
        if !self.previous.contains(&key) { return false }
        if self.builds >= MAX_BUILDS_PER_FRAME {
            knife_perf::add(Metric::TextCacheFallback, 0, 7);
            return false;
        }
        self.builds += 1;
        if !r.text_cache_available().unwrap_or(false) {
            knife_perf::add(Metric::TextCacheFallback, 0, 6);
            return false;
        }
        let logical = [rect[2] as u32, rect[3] as u32];
        let physical = [logical[0] / 2, logical[1] / 2];
        let Some(bytes) = charge(physical) else { return false };
        if bytes > memory_budget::GPU_TEXT_BYTES { return false }
        // Recycle a cold matching surface when admission/capacity would require
        // eviction anyway. Recorded readers retain owners and native WAR fences.
        let pressured = self.bytes + bytes > memory_budget::GPU_TEXT_BYTES
            || self.entries.len() >= memory_budget::GPU_TEXT_ENTRIES
            || r.vita_cache_headroom().unwrap_or(0) < bytes + memory_budget::GPU_CACHE_SPARE_BYTES;
        let recycled = if pressured {
            self.entries.iter().enumerate().filter(|(_, entry)| entry.last_used != self.epoch
                && entry.target.tex.width == logical[0] && entry.target.tex.height == logical[1]
                && entry.target.tex.physical_size() == physical)
                .min_by_key(|(_, entry)| entry.last_used).map(|(index, _)| index)
                .map(|index| self.take(index).target)
        } else { None };
        // A failed promotion must keep its useful small-prefix fallback. Check
        // native room before retiring any old representation for the large run.
        let promotion_admitted = promoted && recycled.is_none();
        if promotion_admitted && !r.vita_prepare_cache_allocation(enc, quads, bytes).unwrap_or(false) {
            knife_perf::add(Metric::TextCacheFallback, 0, 8); return false;
        }
        self.trim(memory_budget::GPU_TEXT_BYTES.saturating_sub(bytes));
        while self.entries.len() >= memory_budget::GPU_TEXT_ENTRIES {
            let victim = self.entries.iter().enumerate()
                .filter(|(_, entry)| entry.last_used != self.epoch)
                .min_by_key(|(_, entry)| entry.last_used).map(|(index, _)| index);
            let Some(victim) = victim else {
                knife_perf::add(Metric::TextCacheFallback, 0, 2);
                return false;
            };
            self.remove(victim);
        }
        if self.bytes + bytes > memory_budget::GPU_TEXT_BYTES {
            knife_perf::add(Metric::TextCacheFallback, 0, 3);
            return false;
        }
        let build = Scope::new(Metric::TextCacheBuild);
        let target = match recycled {
            Some(target) => {
                knife_perf::add(Metric::TextCacheTargetReuse, bytes as u64, 1);
                target
            }
            None => {
                if !promotion_admitted && !r.vita_prepare_cache_allocation(enc, quads, bytes).unwrap_or(false) {
                    knife_perf::add(Metric::TextCacheFallback, 0, 8); return false;
                }
                match r.try_create_scene_target(logical[0], logical[1], "text cache") {
                    Ok(target) => target,
                    Err(_) => { knife_perf::add(Metric::TextCacheFallback, 0, 4); return false }
                }
            }
        };
        let mut shifted = quads.to_vec();
        for quad in &mut shifted {
            for position in &mut quad.pos {
                position[0] -= rect[0];
                position[1] -= rect[1];
            }
        }
        // Dedicated coverage-over alpha: the game's Alpha keeps destination
        // alpha and its Over adds alphas. Neither can create this coverage mask.
        let source_draws = match r.try_draw_text_cache(enc, &target, &shifted) {
            Ok(draws) => draws,
            Err(_) => { knife_perf::add(Metric::TextCacheFallback, 0, 5); return false }
        };
        if r.try_composite_text_cache(enc, canvas, &target, rect).is_err() {
            knife_perf::add(Metric::TextCacheFallback, 0, 5);
            return false;
        }
        let mut sources: Vec<Weak<GpuTexture>> = Vec::new();
        for quad in quads {
            let source = Arc::downgrade(&quad.tex);
            if !sources.iter().any(|existing| existing.ptr_eq(&source)) { sources.push(source); }
        }
        self.entries.push(Entry { key: key.clone(), sources, target, bytes, source_draws,
            last_used: self.epoch, promoted });
        self.bytes += bytes;
        if promoted {
            self.retire_covered_segments(quads, &key);
            knife_perf::add(Metric::TextCachePromote, bytes as u64, quads.len() as u64);
        }
        self.gauges();
        build.finish(bytes as u64, quads.len() as u64);
        true
    }

    /// The promoted surface replaces precisely these old immutable segments.
    /// Do not retain both representations until a later pressure sweep. Any
    /// segment already sampled by another draw_ui call this frame stays pinned.
    fn retire_covered_segments(&mut self, quads: &[Quad], promoted: &Key) {
        let mut begin = 0;
        while begin < quads.len() {
            let mut end = begin + 1;
            while end < quads.len() && same_line(&quads[end - 1], &quads[end]) { end += 1; }
            for segment in quads[begin..end].chunks(MIN_GLYPHS) {
                if segment.len() != MIN_GLYPHS { continue; }
                let Some(rect) = bounds(segment) else { continue; };
                self.key_scratch.clear();
                self.key_scratch.extend([segment.len() as u64, rect[2].to_bits() as u64, rect[3].to_bits() as u64]);
                for q in segment { append_key(&mut self.key_scratch, q, rect); }
                if let Some(index) = self.entries.iter().position(|entry| !entry.promoted
                    && entry.last_used != self.epoch && entry.key != *promoted
                    && entry.key.0.as_ref() == self.key_scratch.as_slice()) {
                    self.remove(index);
                }
            }
            begin = end;
        }
    }
}

/// This fixed layout covers every field admitted by eligible(): Alpha blend,
/// no rule/clip/soft/mask. The origin is an exact physical-pixel boundary; all
/// glyph positions and their mutual overlaps keep their original raster phase.
fn append_key(words: &mut Vec<u64>, q: &Quad, rect: [f32; 4]) {
    let (id, generation) = q.tex.render_identity();
    words.extend([id as u64, generation, q.tex.width as u64, q.tex.height as u64]);
    words.extend(q.tex.physical_size().map(u64::from));
    words.push(q.shade as u64);
    for p in q.pos {
        words.extend([(p[0] - rect[0]).to_bits() as u64, (p[1] - rect[1]).to_bits() as u64]);
    }
    for p in q.uv { words.extend(p.map(|v| v.to_bits() as u64)); }
    words.extend(q.color.map(|v| v.to_bits() as u64));
    for p in q.haze { words.extend(p.map(|v| v.to_bits() as u64)); }
}

fn eligible(quad: &Quad) -> bool {
    matches!(quad.shade, Shade::Text | Shade::RimText) && quad.blend == Blend::Alpha
        && quad.clip.is_none() && quad.rule.is_none() && quad.soft.is_none() && !quad.masked
}

/// A clear vertical jump starts another segment row. This is a scheduling
/// boundary only: superscripts/large wobble may split a row conservatively, but
/// no glyph is moved or reordered. Removing a scrolled-off row cannot shift the
/// canonical eight-glyph boundaries of every following visible row.
fn same_line(a: &Quad, b: &Quad) -> bool {
    let span = |q: &Quad| {
        let min = q.pos.iter().map(|p| p[1]).fold(f32::INFINITY, f32::min);
        let max = q.pos.iter().map(|p| p[1]).fold(f32::NEG_INFINITY, f32::max);
        ((min + max) * 0.5, max - min)
    };
    let ((ay, ah), (by, bh)) = (span(a), span(b));
    (by - ay).abs() <= ah.max(bh) * 0.5
}

/// Integer physical-pixel origin preserves the original raster phase. One pixel
/// of transparent margin keeps bilinear filtering inside the cached image.
fn bounds(quads: &[Quad]) -> Option<[f32; 4]> {
    let mut min = [f32::INFINITY; 2];
    let mut max = [f32::NEG_INFINITY; 2];
    for quad in quads {
        for position in quad.pos {
            for axis in 0..2 {
                if !position[axis].is_finite() { return None }
                min[axis] = min[axis].min(position[axis]);
                max[axis] = max[axis].max(position[axis]);
            }
        }
    }
    let x = ((min[0] * 0.5).floor() - 1.0).max(0.0) * 2.0;
    let y = ((min[1] * 0.5).floor() - 1.0).max(0.0) * 2.0;
    let right = ((max[0] * 0.5).ceil() + 1.0).min(CANVAS_W as f32 * 0.5) * 2.0;
    let bottom = ((max[1] * 0.5).ceil() + 1.0).min(CANVAS_H as f32 * 0.5) * 2.0;
    (right > x && bottom > y).then_some([x, y, right - x, bottom - y])
}

fn charge([width, height]: [u32; 2]) -> Option<usize> {
    let pitch = width.checked_add(7)? & !7;
    let bytes = pitch.checked_mul(height)?.checked_mul(4)?;
    #[cfg(not(test))]
    let charged = knife_platform_vita::gxm::Gxm::texture_charge(bytes).ok()?;
    #[cfg(test)]
    let charged = crate::vita::test_backend::Gxm::texture_charge(bytes).ok()?;
    Some(charged as usize)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vita::{Upload, test_backend::{Control, EffectBlend, EffectShader, Event, Gxm}};

    fn setup() -> (Renderer, Control, RenderTarget, Vec<Quad>) {
        let gxm = Gxm::new().unwrap();
        let control = gxm.control.clone();
        control.borrow_mut().shader_capabilities |= (1 << 11) | (1 << 24) | (1 << 28);
        let renderer = Renderer::new_with_gxm(gxm).unwrap();
        let canvas = renderer.create_composite_target(CANVAS_W, CANVAS_H, "canvas");
        let atlas = renderer.upload(32, 32, Upload::R8(&[255; 1024]), "text test");
        let glyphs = (0..8).map(|i| {
            let mut q = Quad::rect(atlas.clone(),
                [20.25 + i as f32 * 13.0, 40.5, 14.0, 20.0], [0.7, 0.6, 0.5, 0.8]);
            q.shade = Shade::RimText;
            q.haze = [[i as f32 / 32.0, 0.0, (i + 1) as f32 / 32.0, 1.0],
                [0.01, 0.01, 0.4, 0x112233 as f32]];
            q
        }).collect();
        (renderer, control, canvas, glyphs)
    }

    fn frame(pool: &mut Pool, r: &mut Renderer, canvas: &RenderTarget, glyphs: &[Quad]) {
        pool.begin_frame();
        let mut encoder = r.encoder();
        pool.draw_ui(r, &mut encoder, canvas, glyphs, false);
        r.try_present(encoder, canvas).unwrap();
    }

    #[test]
    fn text_cache_source_draw_counts_rim_page_replaces_glyph_draws_with_one_premultiplied_sample() {
        let (mut r, control, canvas, glyphs) = setup();
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert_eq!(pool.entries.len(), 0, "first/dynamic frame remains direct");
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert_eq!(pool.entries.len(), 1);
        assert_eq!(pool.entries[0].source_draws, 1);
        assert!(control.borrow().events.iter().any(|event| matches!(event,
            Event::Draw { shader: EffectShader::RimTextBatched, blend: EffectBlend::CoverageOver, .. })));
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        let trace = control.borrow();
        assert_eq!(trace.events.iter().filter(|event| matches!(event,
            Event::Draw { shader: EffectShader::Alter, blend: EffectBlend::Alpha, .. })).count(), 1);
        assert!(!trace.events.iter().any(|event| matches!(event,
            Event::Draw { shader: EffectShader::Text | EffectShader::RimTextBatched, .. })));
        assert_eq!(pool.entries[0].target.tex.physical_size(),
            [(bounds(&glyphs).unwrap()[2] / 2.0) as u32, (bounds(&glyphs).unwrap()[3] / 2.0) as u32]);
    }

    #[test]
    fn text_cache_source_draw_counts_already_merged_plain_text_does_not_overstate_savings() {
        let (mut r, _control, canvas, mut glyphs) = setup();
        for quad in &mut glyphs { quad.shade = Shade::Text; quad.haze = [[0.0; 4]; 2]; }
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert_eq!(pool.entries.len(), 1);
        assert_eq!(pool.entries[0].source_draws, 1, "the eight plain glyphs already batch into one draw");
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert_eq!(pool.entries[0].source_draws.saturating_sub(1), 0);
    }

    #[test]
    fn text_cache_reveal_fade_wobble_edge_and_atlas_mutations_invalidate_exact_key() {
        let (mut r, _control, canvas, original) = setup();
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &original);
        frame(&mut pool, &mut r, &canvas, &original);
        assert_eq!(pool.entries.len(), 1);
        let original_key = pool.entries[0].key.clone();
        for kind in 0..5 {
            let mut changed = original.clone();
            match kind {
                0 => changed[0].color[3] = 0.5,
                1 => changed[0].pos[0][0] += 0.125,
                2 => changed[0].haze[1][3] += 1.0,
                3 => changed[0].uv[0][0] += 0.001,
                _ => changed[0].tex.native.changed(),
            }
            frame(&mut pool, &mut r, &canvas, &changed);
            assert!(pool.observed.iter().all(|key| *key != original_key));
            assert_eq!(pool.entries.len(), 1, "changing text must not allocate a cache every frame");
        }
    }

    #[test]
    fn text_cache_trim_preserves_current_frame_readers_and_releases_next_frame() {
        let (mut r, _control, canvas, glyphs) = setup();
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        frame(&mut pool, &mut r, &canvas, &glyphs);
        let bytes = pool.bytes();
        pool.trim(0);
        assert_eq!(pool.bytes(), bytes);
        pool.begin_frame();
        pool.trim(0);
        assert_eq!(pool.bytes(), 0);
        assert!(pool.entries.is_empty());
    }

    #[test]
    fn text_cache_resource_barrier_releases_recent_pool_ownership_but_keeps_recorded_readers() {
        let (mut r,control,canvas,glyphs)=setup();
        let mut pool=Pool::default();
        frame(&mut pool,&mut r,&canvas,&glyphs);
        frame(&mut pool,&mut r,&canvas,&glyphs);
        assert!(pool.bytes()>0);
        pool.begin_frame();
        let cached=std::rc::Rc::downgrade(&pool.entries[0].target.tex.native);
        let mut encoder=r.encoder();pool.draw_ui(&mut r,&mut encoder,&canvas,&glyphs,false);
        let bytes=pool.bytes();
        assert_eq!(pool.release_for_images(),bytes);
        assert_eq!(pool.bytes(),0);assert!(pool.entries.is_empty());
        assert!(cached.upgrade().is_some(),"recorded command must keep the sampled owner alive");
        r.try_present(encoder,&canvas).unwrap();
        assert!(cached.upgrade().is_none());
        assert!(control.borrow().events.iter().any(|e|matches!(e,Event::Destroy(_))));
        frame(&mut pool,&mut r,&canvas,&glyphs); // cache miss draws original glyphs
    }

    #[test]
    fn text_cache_missing_passthrough_shader_keeps_original_glyphs() {
        let (mut r, control, canvas, glyphs) = setup();
        control.borrow_mut().shader_capabilities &= !(1 << 24);
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert!(pool.entries.is_empty());
        let trace = control.borrow();
        assert!(!trace.events.iter().any(|event| matches!(event, Event::Create { .. })));
        assert_eq!(trace.events.iter().filter(|event| matches!(event,
            Event::Draw { shader: EffectShader::RimTextBatched, vertices, .. } if vertices.len() == 8 * 6)).count(), 1);
    }

    #[test]
    fn text_cache_bounds_preserve_raster_phase_and_clip_only_outside_canvas() {
        let (_r, _control, _canvas, mut glyphs) = setup();
        let rect = bounds(&glyphs).unwrap();
        assert_eq!(rect, [18.0, 38.0, 110.0, 26.0]);
        for q in &glyphs {
            for position in q.pos {
                for axis in 0..2 {
                    let original = position[axis] * 0.5;
                    let shifted = (position[axis] - rect[axis]) * 0.5;
                    assert_eq!(original.fract(), shifted.fract());
                }
            }
        }
        glyphs[0].pos[0] = [-15.0, -17.0];
        let rect = bounds(&glyphs).unwrap();
        assert_eq!(rect[0..2], [0.0, 0.0]);
    }

    #[test]
    fn text_cache_preserves_window_text_cursor_draw_order() {
        let (mut r, control, canvas, glyphs) = setup();
        let mut ui = vec![Quad::rect(r.white.clone(), [0.0, 0.0, 200.0, 80.0], [0.2; 4])];
        ui.extend(glyphs);
        ui.push(Quad::rect(r.white.clone(), [150.0, 50.0, 8.0, 8.0], [1.0; 4]));
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &ui);
        frame(&mut pool, &mut r, &canvas, &ui);
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &ui);
        let shaders: Vec<_> = control.borrow().events.iter().filter_map(|event| match event {
            Event::Draw { shader, .. } => Some(*shader), _ => None,
        }).collect();
        assert_eq!(shaders, [EffectShader::Sprite, EffectShader::Alter, EffectShader::Sprite]);
    }

    #[test]
    fn typing_prefixes_survive_reveals_and_finished_run_retires_their_old_surfaces() {
        let (mut r, control, canvas, first) = setup();
        let mut glyphs = first.clone();
        for i in 8..17 {
            let mut q = first[0].clone();
            for p in &mut q.pos { p[0] += i as f32 * 13.; }
            glyphs.push(q);
        }
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs[..16]);
        frame(&mut pool, &mut r, &canvas, &glyphs[..16]);
        assert_eq!(pool.entries.len(), 2);
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        assert_eq!(pool.entries.len(), 2, "one new character must not rebake stable prefixes");
        assert!(!control.borrow().events.iter().any(|e| matches!(e, Event::Create { .. })));
        for _ in 0..2 {
            pool.begin_frame();
            let mut enc = r.encoder();
            pool.draw_ui(&mut r, &mut enc, &canvas, &glyphs, true);
            r.try_present(enc, &canvas).unwrap();
        }
        assert_eq!(pool.entries.len(), 1, "finished run replaces rather than retains duplicate prefixes");
        assert!(pool.entries[0].promoted);
    }

    #[test]
    fn scroll_reuses_only_integer_physical_pixel_translations() {
        let (mut r, control, canvas, glyphs) = setup();
        let mut pool = Pool::default();
        frame(&mut pool, &mut r, &canvas, &glyphs);
        frame(&mut pool, &mut r, &canvas, &glyphs);
        let key = pool.entries[0].key.clone();
        let mut scrolled = glyphs;
        for q in &mut scrolled { for p in &mut q.pos { p[0] += 20.; p[1] += 4.; } }
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &scrolled);
        assert!(pool.observed.iter().any(|observed| observed == &key));
        assert!(!control.borrow().events.iter().any(|e| matches!(e,
            Event::Draw { shader: EffectShader::RimTextBatched, .. } | Event::Create { .. })));
        for q in &mut scrolled { for p in &mut q.pos { p[0] += 0.5; } }
        control.borrow_mut().events.clear();
        frame(&mut pool, &mut r, &canvas, &scrolled);
        assert!(pool.observed.iter().all(|observed| observed != &key));
        assert!(control.borrow().events.iter().any(|e| matches!(e,
            Event::Draw { shader: EffectShader::RimTextBatched, .. })));
    }

    #[test]
    fn ruby_and_short_lines_keep_glyph_geometry_and_order_without_partial_cache() {
        let (mut r, control, canvas, mut glyphs) = setup();
        // Four normal glyphs, two ruby glyphs, then a separate short line.
        // Geometry, rather than language or font indices, defines row splits.
        for (i, q) in glyphs.iter_mut().enumerate() {
            q.color[0] = i as f32 / 16.;
            if (4..6).contains(&i) { for p in &mut q.pos { p[1] -= 20.; } }
            if i >= 6 { for p in &mut q.pos { p[1] += 50.; } }
        }
        let mut pool = Pool::default();
        for _ in 0..2 {
            control.borrow_mut().events.clear();
            frame(&mut pool, &mut r, &canvas, &glyphs);
            assert!(pool.entries.is_empty(), "each unfinished row is shorter than eight glyphs");
            let trace = control.borrow();
            let vertices: Vec<_> = trace.events.iter().filter_map(|e| match e {
                Event::Draw { shader: EffectShader::RimTextBatched, vertices, .. } => Some(vertices), _ => None,
            }).flatten().collect();
            assert_eq!(vertices.len(), 8 * 6);
            for (i, v) in vertices.chunks_exact(6).enumerate() {
                assert!(v.iter().all(|vertex| vertex.color[0] == i as f32 / 16.));
                assert!((v[0].pos[1] - (1. - glyphs[i].pos[0][1] / 540.)).abs() < 0.00001);
            }
        }
    }

    #[test]
    fn text_cache_coverage_over_then_passthrough_matches_direct_rgb_and_keeps_canvas_alpha() {
        let glyphs: [([f32; 3], f32); 2] = [([0.14, 0.07, 0.21], 0.35), ([0.3, 0.2, 0.1], 0.5)];
        let background: [f32; 3] = [0.2, 0.4, 0.6];
        let mut direct = background;
        let (mut cached, mut alpha) = ([0.0; 3], 0.0);
        for (rgb, a) in glyphs {
            for channel in 0..3 {
                direct[channel] = rgb[channel] + direct[channel] * (1.0 - a);
                cached[channel] = rgb[channel] + cached[channel] * (1.0 - a);
            }
            alpha = a + alpha * (1.0 - a);
        }
        for channel in 0..3 {
            let composite = cached[channel] + background[channel] * (1.0 - alpha);
            assert!((composite - direct[channel]).abs() < 1e-6_f32);
            let wrongly_multiplied_twice = cached[channel] * alpha
                + background[channel] * (1.0 - alpha);
            assert!((wrongly_multiplied_twice - direct[channel]).abs() > 0.01);
        }
        assert!((alpha - 0.675).abs() < 1e-6);
        assert!((alpha - (glyphs[0].1 + glyphs[1].1)).abs() > 0.1,
            "the game's additive-alpha Over cannot build this cache");
    }
}

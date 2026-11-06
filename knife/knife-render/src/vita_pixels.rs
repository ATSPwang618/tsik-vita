//! Exact storage selection for immutable CPU-baked images. No quantization.
pub fn opaque_rgba(width: u32, height: u32, pixels: &[u8]) -> bool {
    let length = (width as usize).checked_mul(height as usize).and_then(|n| n.checked_mul(4));
    width != 0 && height != 0 && length == Some(pixels.len())
        && pixels.chunks_exact(4).all(|pixel| pixel[3] == 255)
}

pub fn storage_bpp(width: u32, height: u32, pixels: &[u8]) -> u32 {
    if opaque_rgba(width, height, pixels) { 3 } else { 4 }
}

/// Complete RGBA identities, including RGB hidden under zero alpha. Bounded
/// open addressing avoids a heap allocation and stops on the 257th colour.
pub fn palette_colors(width: u32, height: u32, pixels: &[u8]) -> Option<usize> {
    let length = (width as usize).checked_mul(height as usize)?.checked_mul(4)?;
    if width == 0 || height == 0 || pixels.len() != length { return None; }
    let mut colors = [0u32; 512];
    let mut used = [false; 512];
    let mut count = 0;
    for pixel in pixels.chunks_exact(4) {
        let color = u32::from_le_bytes(pixel.try_into().unwrap());
        let mut slot = (color.wrapping_mul(2654435761) >> 23) as usize;
        while used[slot] && colors[slot] != color { slot = (slot + 1) & 511; }
        if !used[slot] {
            count += 1;
            if count > 256 { return None; }
            used[slot] = true; colors[slot] = color;
        }
    }
    Some(count)
}

pub fn indexed_bytes(width: u32, height: u32) -> Option<u32> {
    let indices = width.checked_add(7)?.checked_div(8)?.checked_mul(8)?.checked_mul(height)?;
    indices.checked_add(63).map(|n| n & !63)?.checked_add(1024)
}

/// Use a palette only if it saves a complete CDRAM page even compared with
/// opaque RGB24. Tiny images keep ordinary storage and avoid palette overhead.
pub fn indexed_rgba(width: u32, height: u32, pixels: &[u8]) -> bool {
    let Some(indexed) = indexed_bytes(width,height) else { return false; };
    let Some(original) = width.checked_add(7).map(|n| n & !7)
        .and_then(|n| n.checked_mul(height)).and_then(|n| n.checked_mul(storage_bpp(width,height,pixels)))
        else { return false; };
    indexed.div_ceil(256*1024) < original.div_ceil(256*1024)
        && palette_colors(width,height,pixels).is_some()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn opaque_rgb_keeps_every_colour_bit_and_uses_three_bytes() {
        let pixels = [1, 2, 3, 255, 254, 253, 252, 255];
        assert!(opaque_rgba(2, 1, &pixels));
        assert_eq!(storage_bpp(2, 1, &pixels), 3);
    }
    #[test]
    fn alpha_edges_and_invalid_layouts_keep_rgba_storage() {
        for alpha in [0, 1, 127, 254] {
            assert_eq!(storage_bpp(2, 1, &[1, 2, 3, 255, 4, 5, 6, alpha]), 4);
        }
        assert!(!opaque_rgba(0,1,&[]));
        assert!(!opaque_rgba(2,1,&[255;7]));
        assert!(!opaque_rgba(1,1,&[255;8]));
        assert!(!opaque_rgba(u32::MAX,u32::MAX,&[]));
    }

    #[test]
    fn palette_preserves_all_alpha_values_and_rejects_colour_257() {
        let mut px = Vec::new();
        for _ in 0..400 { for alpha in 0..=255 { px.extend_from_slice(&[19,37,91,alpha]); } }
        assert_eq!(palette_colors(256,400,&px),Some(256));
        assert!(indexed_rgba(256,400,&px));
        px[0]=20; // distinct RGB even though its alpha is zero
        assert_eq!(palette_colors(256,400,&px),None);
        assert!(!indexed_rgba(256,400,&px));
        assert!(!indexed_rgba(1,1,&[19,37,91,0]));
        assert_eq!(palette_colors(2,1,&[19;7]),None);
        assert_eq!(palette_colors(u32::MAX,u32::MAX,&[]),None);
    }
}

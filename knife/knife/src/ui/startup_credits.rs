//! Timing for the optional Tsukihime contributor image in parts.mrg.

pub const PARTS_INDEX: usize = 5;
const FADE_FRAMES: f32 = 30.0;
// Half a second in, seven seconds readable, half a second out at 60 Hz.
const HOLD_FRAMES: f32 = 420.0;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Credits {
    alpha: f32,
    held: f32,
    out: bool,
}

impl Credits {
    pub fn new() -> Self {
        Self { alpha: 0.0, held: 0.0, out: false }
    }

    pub fn alpha(self) -> f32 { self.alpha }

    pub fn dismiss(&mut self) { self.out = true; }

    /// Frames use the same 60 Hz time scale as the existing intro screens.
    /// Return true once the fade to black finishes, allowing the original boot.
    pub fn advance(&mut self, frames: f32) -> bool {
        let frames = frames.max(0.0);
        if self.out {
            self.alpha = (self.alpha - frames / FADE_FRAMES).max(0.0);
            return self.alpha == 0.0;
        }
        self.alpha = (self.alpha + frames / FADE_FRAMES).min(1.0);
        if self.alpha >= 1.0 {
            self.held += frames;
            self.out = self.held >= HOLD_FRAMES;
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starts_black_and_fades_in() {
        let mut credits = Credits::new();
        assert_eq!(credits.alpha(), 0.0);
        for _ in 0..31 { assert!(!credits.advance(1.0)); }
        assert_eq!(credits.alpha(), 1.0);
    }

    #[test]
    fn automatic_screen_returns_to_boot_in_about_eight_seconds() {
        let mut credits = Credits::new();
        let done = (1..=500).find(|_| credits.advance(1.0)).unwrap();
        assert!((478..=482).contains(&done), "completed at {done} frames");
        assert_eq!(credits.alpha(), 0.0);
    }

    #[test]
    fn confirmation_fades_out_without_waiting_for_the_hold() {
        let mut credits = Credits::new();
        for _ in 0..40 { credits.advance(1.0); }
        credits.dismiss();
        let done = (1..=32).find(|_| credits.advance(1.0)).unwrap();
        assert!(done <= 31);
        assert_eq!(credits.alpha(), 0.0);
    }

    #[test]
    fn early_confirmation_does_not_flash_the_image() {
        let mut credits = Credits::new();
        credits.dismiss();
        assert!(credits.advance(1.0));
        assert_eq!(credits.alpha(), 0.0);
    }

    #[test]
    fn variable_frame_steps_finish_without_out_of_range_alpha() {
        let mut credits = Credits::new();
        let mut elapsed = 0.0;
        loop {
            elapsed += 2.5;
            let done = credits.advance(2.5);
            assert!((0.0..=1.0).contains(&credits.alpha()));
            if done { break; }
            assert!(elapsed < 490.0);
        }
        assert!((475.0..=487.5).contains(&elapsed), "completed at {elapsed} frames");
    }
}

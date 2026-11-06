//! Native 8-bit pad axes, shared with the host regression probe.
pub fn axis(value: u8) -> i32 {
    let value = i32::from(value) - 128;
    let magnitude = value.abs();
    if magnitude <= 16 { return 0; }
    let limit = if value < 0 { 128 } else { 127 };
    value.signum() * (magnitude - 16) * limit / (limit - 16)
}

#[cfg(test)]
mod tests {
    use super::axis;
    #[test]
    fn resting_pad_noise_cannot_pan_a_gallery_picture() {
        for raw in 112..=144 { assert_eq!(axis(raw), 0, "raw axis {raw}"); }
    }
    #[test]
    fn deliberate_motion_keeps_direction_range_and_order() {
        assert_eq!(axis(0), -128);
        assert_eq!(axis(255), 127);
        assert!(axis(100) < 0 && axis(156) > 0);
        for raw in 0..255 { assert!(axis(raw) <= axis(raw+1)); }
    }
}

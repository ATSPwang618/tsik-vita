//! Shared cache ceilings. Native admission also checks the kernel's free CDRAM;
//! these are limits, never eagerly allocated reservations.
pub const MIB: usize = 1024 * 1024;
pub const CPU_SOURCE_BYTES: usize = 64 * MIB;
pub const CPU_GRADED_BYTES: usize = 32 * MIB;
pub const CPU_SOUND_BYTES: usize = 16 * MIB;
/// One bounded encoded+PCM decode job, admitted under the normal heap headroom.
pub const CPU_SOUND_PREPARE_BYTES: usize = 40 * MIB;
/// Temporary demand pins (may alias the sound cache); never grow by key count alone.
pub const CPU_SOUND_PREPARED_BYTES: usize = 16 * MIB;
// Metadata only; targets remain owned and budgeted by the visible UI page.
pub const CPU_UI_PASS_CACHE_BYTES: usize = 256 * 1024;
pub const CPU_UI_PASS_CACHE_ENTRIES: usize = 16;
pub const GPU_RESOURCE_BYTES: usize = 56 * MIB;
pub const GPU_SOURCE_BYTES: usize = 32 * MIB;
pub const GPU_TEXT_BYTES: usize = if cfg!(feature="vita-stable") {4*MIB} else {12*MIB};
pub const GPU_TEXT_ENTRIES: usize = if cfg!(feature="vita-stable") {16} else {32};
/// Exact pre-tone grey curves shared by brightness/contrast kernel variants.
pub const CPU_GRADE_BASE_BYTES: usize = 3 * MIB;
pub const GPU_GROUP_BYTES: usize = if cfg!(feature="vita-stable") {4*MIB} else {12*MIB};
pub const GPU_GROUP_ENTRIES: usize = if cfg!(feature="vita-stable") {2} else {6};
/// One optional native540p static prefix. Kernel headroom is checked before allocation.
pub const GPU_STAGE_PREFIX_BYTES: usize = if cfg!(feature="vita-stable") {0} else {3*MIB};
/// Spare stage + composite outputs; each uses the native pitch/alignment.
/// Allocated lazily under kernel/JPEG admission, never for history targets.
pub const GPU_TARGET_RING_BYTES: usize = if cfg!(feature="vita-stable") {0} else {6*MIB};
/// One native540p movie-frame cache, updated only for new decoder frames.
pub const GPU_MOVIE_FRAME_BYTES: usize = 3 * MIB;
pub const GPU_PRESSURE_HEADROOM: usize = if cfg!(feature="vita-stable") {16*MIB} else {8*MIB};
pub const GPU_CACHE_SPARE_BYTES: usize = if cfg!(feature="vita-stable") {8*MIB} else {MIB};
pub const CPU_PRESSURE_HEADROOM: usize = 32 * MIB;
pub const CPU_TARGET_HEADROOM: usize = 48 * MIB;

#[cfg(all(test,feature="vita-stable"))]
mod stable_tests {
    use super::*;
    #[test]
    fn optional_gpu_caches_yield_room_for_forty_old_and_new_story_layers() {
        assert_eq!(GPU_TARGET_RING_BYTES,0);
        assert_eq!(GPU_STAGE_PREFIX_BYTES,0);
        assert!(GPU_TEXT_BYTES<=4*MIB && GPU_TEXT_ENTRIES<=16);
        assert!(GPU_GROUP_BYTES<=4*MIB && GPU_GROUP_ENTRIES<=2);
        assert!(GPU_PRESSURE_HEADROOM>=16*MIB);
        assert!(GPU_CACHE_SPARE_BYTES>=8*MIB);
        assert!(40*2*512*1024<=GPU_RESOURCE_BYTES);
    }
}

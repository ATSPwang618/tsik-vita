//! Read-only, seekable game files. Vita's newlib off_t is signed 32-bit;
//! archive lengths and positions must use the SDK's SceOff/i64 interface.
use std::io;

#[cfg(any(target_os = "vita", test))]
#[path = "file_io_native.rs"]
mod native;

#[cfg(target_os = "vita")]
pub use native::NativeFile as ReadFile;
#[cfg(not(target_os = "vita"))]
pub use std::fs::File as ReadFile;

/// Query length without moving the read cursor or narrowing a Vita offset.
pub fn file_len(file: &mut ReadFile) -> io::Result<u64> {
    #[cfg(target_os = "vita")]
    { file.len64() }
    #[cfg(not(target_os = "vita"))]
    { file.metadata().map(|metadata| metadata.len()) }
}

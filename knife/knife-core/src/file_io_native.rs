use std::{ffi::CString, io::{self, Read, Seek, SeekFrom}, path::Path};

#[cfg(target_os = "vita")]
mod sdk {
    #[link(name = "SceIofilemgr_stub", kind = "static")]
    unsafe extern "C" {
        pub fn sceIoOpen(path: *const std::ffi::c_char, flags: i32, mode: i32) -> i32;
        pub fn sceIoClose(fd: i32) -> i32;
        pub fn sceIoRead(fd: i32, buffer: *mut std::ffi::c_void, bytes: u32) -> i32;
        pub fn sceIoLseek(fd: i32, offset: i64, whence: i32) -> i64;
    }
}

pub struct NativeFile { fd: i32 }

fn sdk_error(operation: &str, code: i64) -> io::Error {
    let kind = if (code as u32) & 0xffff_0000 == 0x8001_0000 {
        io::Error::from_raw_os_error((code as u32 & 0xffff) as i32).kind()
    } else { io::ErrorKind::Other };
    io::Error::new(kind, format!("{operation}: Vita IO status {:#010x}", code as u32))
}

impl NativeFile {
    pub fn open(path: impl AsRef<Path>) -> io::Result<Self> {
        let path = CString::new(path.as_ref().as_os_str().as_encoded_bytes())
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "file path contains NUL"))?;
        // SAFETY: NUL-terminated path is live for this synchronous call. The
        // returned SceUID is owned here; it is never treated as a newlib fd.
        let fd = unsafe { sdk::sceIoOpen(path.as_ptr(), 1, 0) }; // SCE_O_RDONLY
        if fd < 0 { return Err(sdk_error("sceIoOpen", i64::from(fd))); }
        Ok(Self { fd })
    }

    pub fn len64(&mut self) -> io::Result<u64> {
        let position = self.seek(SeekFrom::Current(0))?;
        let length = self.seek(SeekFrom::End(0));
        let restored = self.seek(SeekFrom::Start(position));
        let length = length?;
        restored?;
        Ok(length)
    }
}

impl Read for NativeFile {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        if buffer.is_empty() { return Ok(0); }
        let count = buffer.len().min(i32::MAX as usize) as u32;
        // SAFETY: SDK borrows at most count writable bytes and retains no pointer.
        let result = unsafe { sdk::sceIoRead(self.fd, buffer.as_mut_ptr().cast(), count) };
        if result < 0 { return Err(sdk_error("sceIoRead", i64::from(result))); }
        if result as u32 > count { return Err(io::Error::new(io::ErrorKind::InvalidData, "SDK read exceeded buffer")); }
        Ok(result as usize)
    }
}

impl Seek for NativeFile {
    fn seek(&mut self, from: SeekFrom) -> io::Result<u64> {
        let (offset, whence) = match from {
            SeekFrom::Start(offset) => (i64::try_from(offset)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "file offset exceeds SceOff"))?, 0),
            SeekFrom::Current(offset) => (offset, 1),
            SeekFrom::End(offset) => (offset, 2),
        };
        // SAFETY: fd remains owned. SceOff is i64, including on the 32-bit CPU;
        // neither the argument nor result passes through newlib lseek/off_t.
        let position = unsafe { sdk::sceIoLseek(self.fd, offset, whence) };
        if position < 0 { return Err(sdk_error("sceIoLseek", position)); }
        Ok(position as u64)
    }
}

impl Drop for NativeFile {
    fn drop(&mut self) {
        // SAFETY: this wrapper owns the SceUID once; close never uses newlib.
        let _ = unsafe { sdk::sceIoClose(self.fd) };
    }
}

// Host double for this exact wrapper, backed by real sparse files and 64-bit
// host seek. These tests exercise Rust/SceOff boundary handling, not Vita IO.
#[cfg(all(test, not(target_os = "vita")))]
#[allow(non_snake_case)]
mod sdk {
    use std::{collections::HashMap, ffi::{CStr, c_char, c_void}, fs::File,
        io::{Read, Seek, SeekFrom}, sync::{Mutex, OnceLock, atomic::{AtomicI32, Ordering}}};
    fn files() -> &'static Mutex<HashMap<i32, File>> {
        static FILES: OnceLock<Mutex<HashMap<i32, File>>> = OnceLock::new();
        FILES.get_or_init(|| Mutex::new(HashMap::new()))
    }
    pub unsafe fn sceIoOpen(path: *const c_char, flags: i32, _: i32) -> i32 {
        assert_eq!(flags, 1);
        let path = unsafe { CStr::from_ptr(path) }.to_str().unwrap();
        let file = match File::open(path) {
            Ok(file) => file,
            Err(error) => return if error.kind() == std::io::ErrorKind::NotFound { 0x8001_0002u32 as i32 } else { 0x8001_0005u32 as i32 },
        };
        static NEXT: AtomicI32 = AtomicI32::new(100);
        let fd = NEXT.fetch_add(1, Ordering::Relaxed);
        files().lock().unwrap().insert(fd, file); fd
    }
    pub unsafe fn sceIoClose(fd: i32) -> i32 {
        assert!(files().lock().unwrap().remove(&fd).is_some(), "double close"); 0
    }
    pub unsafe fn sceIoRead(fd: i32, buffer: *mut c_void, bytes: u32) -> i32 {
        let buffer = unsafe { std::slice::from_raw_parts_mut(buffer.cast::<u8>(), bytes as usize) };
        files().lock().unwrap().get_mut(&fd).unwrap().read(buffer)
            .map(|n| n as i32).unwrap_or(0x8001_0005u32 as i32)
    }
    pub unsafe fn sceIoLseek(fd: i32, offset: i64, whence: i32) -> i64 {
        let from = match whence {
            0 if offset >= 0 => SeekFrom::Start(offset as u64),
            1 => SeekFrom::Current(offset), 2 => SeekFrom::End(offset),
            _ => return i64::from(0x8001_0016u32 as i32),
        };
        files().lock().unwrap().get_mut(&fd).unwrap().seek(from)
            .map(|n| n as i64).unwrap_or(i64::from(0x8001_0016u32 as i32))
    }
}

#[cfg(all(test, not(target_os = "vita")))]
mod tests {
    use super::*;
    use std::{fs::File, io::Write, path::PathBuf, sync::atomic::{AtomicU64, Ordering}};
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            Self(std::env::temp_dir().join(format!("knife-native-io-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed))))
        }
    }
    impl Drop for Fixture { fn drop(&mut self) { let _ = std::fs::remove_file(&self.0); } }

    #[test]
    #[cfg(unix)] // set_len holes are sparse on the Unix test filesystem.
    fn real_r4_length_and_reads_cross_signed_32bit_boundary_without_moving_length_cursor() {
        let fixture = Fixture::new();
        let mut output = File::create(&fixture.0).unwrap();
        output.set_len(2_475_186_176).unwrap();
        for (offset, data) in [(0x7fff_fffcu64, b"boundary".as_slice()), (2_475_186_168, b"R4tail!!".as_slice())] {
            output.seek(SeekFrom::Start(offset)).unwrap(); output.write_all(data).unwrap();
        }
        drop(output);
        let mut input = NativeFile::open(&fixture.0).unwrap();
        input.seek(SeekFrom::Start(0x7fff_fffc)).unwrap();
        assert_eq!(input.len64().unwrap(), 2_475_186_176);
        let mut bytes = [0; 8]; input.read_exact(&mut bytes).unwrap(); assert_eq!(&bytes, b"boundary");
        input.seek(SeekFrom::End(-8)).unwrap(); input.read_exact(&mut bytes).unwrap(); assert_eq!(&bytes, b"R4tail!!");
        assert_eq!(input.read(&mut bytes).unwrap(), 0);
    }

    #[test]
    #[cfg(unix)]
    fn positions_above_four_gib_and_negative_relative_offsets_keep_all_bits() {
        let fixture = Fixture::new();
        let offset = (1u64 << 32) + 17;
        let mut output = File::create(&fixture.0).unwrap();
        output.seek(SeekFrom::Start(offset)).unwrap(); output.write_all(b"wide").unwrap(); drop(output);
        let mut input = NativeFile::open(&fixture.0).unwrap();
        assert_eq!(input.len64().unwrap(), offset + 4);
        assert_eq!(input.seek(SeekFrom::Start(offset)).unwrap(), offset);
        assert_eq!(input.seek(SeekFrom::Current(4)).unwrap(), offset + 4);
        assert_eq!(input.seek(SeekFrom::Current(-4)).unwrap(), offset);
        let mut data = [0; 4]; input.read_exact(&mut data).unwrap(); assert_eq!(&data, b"wide");
    }

    #[test]
    fn invalid_offsets_and_missing_paths_remain_errors() {
        let fixture = Fixture::new();
        assert_eq!(NativeFile::open(&fixture.0).err().unwrap().kind(), io::ErrorKind::NotFound);
        drop(File::create(&fixture.0).unwrap());
        let mut input = NativeFile::open(&fixture.0).unwrap();
        assert_eq!(input.seek(SeekFrom::Start(u64::MAX)).unwrap_err().kind(), io::ErrorKind::InvalidInput);
        assert!(input.seek(SeekFrom::Current(-1)).is_err());
        assert_eq!(input.seek(SeekFrom::Current(0)).unwrap(), 0);
        assert_eq!(input.read(&mut []).unwrap(), 0);
    }
}

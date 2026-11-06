//! Small tracing bridge to the bounded sceClibPrintf worker (VitaDeck/CatLog).
//! No file, socket, ANSI colour or per-frame subscriber allocation is required.
use std::fmt::{self, Write};
use tracing::{Event, Level, Metadata, Subscriber, field::{Field, Visit},
    span::{Attributes, Id, Record}, subscriber::Interest};

const MAX_RECORD: usize = 2048;

struct Line(String);
impl Write for Line {
    fn write_str(&mut self, text: &str) -> fmt::Result {
        for ch in text.chars() {
            if self.0.len() + ch.len_utf8() > MAX_RECORD { break; }
            // A message cannot inject fake console records or terminal escapes.
            self.0.push(if ch.is_control() { ' ' } else { ch });
        }
        Ok(())
    }
}
impl Visit for Line {
    fn record_debug(&mut self, field: &Field, value: &dyn fmt::Debug) {
        if field.name() == "message" { let _ = write!(self, " {value:?}"); }
        else { let _ = write!(self, " {}={value:?}", field.name()); }
    }
}

struct ConsoleSubscriber { emit: fn(&str) }
impl Subscriber for ConsoleSubscriber {
    fn enabled(&self, metadata: &Metadata<'_>) -> bool { *metadata.level() <= Level::INFO }
    fn register_callsite(&self, metadata: &'static Metadata<'static>) -> Interest {
        if self.enabled(metadata) { Interest::always() } else { Interest::never() }
    }
    fn max_level_hint(&self) -> Option<tracing::metadata::LevelFilter> {
        Some(tracing::metadata::LevelFilter::INFO)
    }
    fn new_span(&self, _: &Attributes<'_>) -> Id { Id::from_u64(1) }
    fn record(&self, _: &Id, _: &Record<'_>) {}
    fn record_follows_from(&self, _: &Id, _: &Id) {}
    fn enter(&self, _: &Id) {}
    fn exit(&self, _: &Id) {}
    fn event(&self, event: &Event<'_>) {
        let mut line = Line(String::with_capacity(256));
        let meta = event.metadata();
        let _ = write!(line, "[TSUKIHIME] {} {}:", meta.level(), meta.target());
        event.record(&mut line);
        line.0.push('\n');
        (self.emit)(&line.0);
    }
}

pub fn install(emit: fn(&str)) -> Result<(), tracing::subscriber::SetGlobalDefaultError> {
    tracing::subscriber::set_global_default(ConsoleSubscriber { emit })
}

#[cfg(test)]
mod tests {
    use super::*;
    static RECEIVED: std::sync::Mutex<Vec<String>> = std::sync::Mutex::new(Vec::new());
    fn capture(line: &str) { RECEIVED.lock().unwrap().push(line.into()); }

    #[test]
    fn ui_errors_and_boot_records_reach_sink_without_debug_spam() {
        RECEIVED.lock().unwrap().clear();
        tracing::subscriber::with_default(ConsoleSubscriber { emit: capture }, || {
            tracing::info!(target: "boot", "ARCHIVES opened");
            tracing::warn!(target: "ui", atlas = "TITLE_PARTS_ZC", "title_bg0 rejected");
            tracing::error!(target: "render", "upload failed");
            tracing::debug!("per-frame details");
            tracing::trace!("more details");
        });
        let rows = RECEIVED.lock().unwrap();
        assert_eq!(rows.len(), 3);
        assert!(rows[0].contains("INFO boot: ARCHIVES opened"));
        assert!(rows[1].contains("WARN ui:") && rows[1].contains("TITLE_PARTS_ZC"));
        assert!(rows[2].contains("ERROR render: upload failed"));
        assert!(rows.iter().all(|s| s.ends_with('\n')));
    }

    #[test]
    fn huge_unicode_fields_are_bounded_and_cannot_inject_console_lines() {
        let mut line = Line(String::new());
        let _ = write!(line, "{}\nFORGED\u{1b}", "图".repeat(4000));
        assert!(line.0.len() <= MAX_RECORD);
        assert!(std::str::from_utf8(line.0.as_bytes()).is_ok());
        let mut controls = Line(String::new());
        let _ = write!(controls, "a\r\nb\t\u{1b}c");
        assert_eq!(controls.0, "a  b  c");
    }
}

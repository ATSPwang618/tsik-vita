fn main() {
    println!("cargo:rerun-if-env-changed=VITASDK");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("vita") {
        let sdk = std::env::var("VITASDK").expect("set VITASDK to the installed SDK root");
        println!("cargo:rustc-link-search=native={sdk}/arm-vita-eabi/lib");
    }
}

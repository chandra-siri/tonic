fn main() {
    tonic_build::configure()
        .bytes(".")
        .compile(
            &["../../../../examples/proto/routeguide/route_guide.proto"],
            &["../../../../examples/proto"],
        )
        .unwrap();
}

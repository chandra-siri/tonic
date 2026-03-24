fn main() {
    tonic_prost_build::configure()
        .bytes(".")
        .compile(
            &["../../../../examples/proto/routeguide/route_guide.proto"],
            &["../../../../examples/proto"],
        )
        .unwrap();
}

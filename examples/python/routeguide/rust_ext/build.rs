fn main() {
    tonic_prost_build::configure()
        .bytes(".")
        .compile_protos(
            &["../../../../examples/proto/routeguide/route_guide.proto"],
            &["../../../../examples/proto"],
        )
        .unwrap();
}

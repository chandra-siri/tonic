"""Python benchmark wrapper driving native Protobuf interactions sequentially over rust FFI!"""

import asyncio
import logging
import statistics
import time

try:
    import routeguide_rust_client
except ImportError:
    print("Could not import routeguide_rust_client. Please build the PyO3 C-extension first!")
    exit(1)

import route_guide_pb2

async def guide_list_features(stub: routeguide_rust_client.RustRouteGuideStub) -> float:
    rectangle = route_guide_pb2.Rectangle(
        lo=route_guide_pb2.Point(latitude=400000000, longitude=-750000000),
        hi=route_guide_pb2.Point(latitude=420000000, longitude=-730000000),
    )

    # Natively compile to bytes for the Rust boundary FFI leap
    payload_bytes = rectangle.SerializeToString()

    print("Starting 5s warmup phase...")
    features_stream = await stub.list_features(payload_bytes)

    warmup_duration = 5.0
    measure_duration = 30.0

    received_bytes = 0
    count = 0
    is_warmup = True

    warmup_start = time.time()
    measure_start = time.time()

    async for container_bytes in features_stream:
        now = time.time()
        
        if is_warmup:
            if now - warmup_start >= warmup_duration:
                print("Warmup complete. Measuring throughput for 30s...")
                is_warmup = False
                measure_start = time.time()
            continue

        # Decrypt from the FFI Yield back natively into a local Python class!
        container = route_guide_pb2.BytesContainer.FromString(container_bytes)
        received_bytes += len(container.data)
        count += 1
        
        if now - measure_start >= measure_duration:
            break

    elapsed = time.time() - measure_start
    mib = received_bytes / (1024.0 * 1024.0)
    throughput = mib / elapsed if elapsed > 0 else 0

    print(f"Total chunks received: {count}")
    print(f"Received {mib:.2f} MiB in {elapsed:.2f}s")
    print(f"Throughput: {throughput:.2f} MiB/s")

    return throughput

async def main() -> None:
    # Notice we pass the full URL spec just as tonic requires natively!
    target = "http://10.128.0.203:10000"
    n = 5
    throughputs = []
    
    print(f"Instantiating PyO3 Rust Wrapper Stub bound to {target}...")
    try:
        stub = await routeguide_rust_client.RustRouteGuideStub.connect(target)
    except Exception as e:
        print(f"Failed to cleanly connect PyO3 to Tonic client stub bridge: {e}")
        return

    print(f"-------------- ListFeatures (Running {n} times) --------------")
    for i in range(n):
        print(f"\n--- Run {i + 1}/{n} ---")
        try:
            throughput = await guide_list_features(stub)
            throughputs.append(throughput)
        except Exception as e:
            print(f"Error during benchmark stream loop {i+1}: {e}")
            break

    if not throughputs:
        print("No throughput data was collected.")
        return

    print("\n-------------- Benchmark Summary --------------")
    print(f"Average Throughput: {statistics.mean(throughputs):.2f} MiB/s")
    print(f"Median Throughput:  {statistics.median(throughputs):.2f} MiB/s")
    print(f"Max Throughput:     {max(throughputs):.2f} MiB/s")
    print(f"Min Throughput:     {min(throughputs):.2f} MiB/s")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

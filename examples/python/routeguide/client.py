"""The Python AsyncIO implementation of the gRPC route guide client focusing on server streaming."""

import asyncio
import logging
import time
import statistics

import grpc
import route_guide_pb2
import route_guide_pb2_grpc


async def guide_list_features(stub: route_guide_pb2_grpc.RouteGuideStub) -> float:
    rectangle = route_guide_pb2.Rectangle(
        lo=route_guide_pb2.Point(latitude=400000000, longitude=-750000000),
        hi=route_guide_pb2.Point(latitude=420000000, longitude=-730000000),
    )

    print("Starting 5s warmup phase...")
    features = stub.ListFeatures(rectangle)

    warmup_duration = 5.0
    measure_duration = 30.0

    received_bytes = 0
    count = 0
    is_warmup = True

    warmup_start = time.time()
    measure_start = time.time()  # Dummy initial value

    async for container in features:
        now = time.time()
        
        if is_warmup:
            if now - warmup_start >= warmup_duration:
                print("Warmup complete. Measuring throughput for 30s...")
                is_warmup = False
                measure_start = time.time()
            continue

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
    # Target address for the server (from client.rs configuration)
    target = "10.128.0.203:10000"
    
    print(f"Connecting to {target}...")
    
    n = 5
    throughputs = []

    async with grpc.aio.insecure_channel(target) as channel:
        stub = route_guide_pb2_grpc.RouteGuideStub(channel)
        print(f"-------------- ListFeatures (Running {n} times) --------------")
        for i in range(n):
            print(f"\n--- Run {i + 1}/{n} ---")
            throughput = await guide_list_features(stub)
            throughputs.append(throughput)

    print("\n-------------- Benchmark Summary --------------")
    print(f"Average Throughput: {statistics.mean(throughputs):.2f} MiB/s")
    print(f"Median Throughput:  {statistics.median(throughputs):.2f} MiB/s")
    print(f"Max Throughput:     {max(throughputs):.2f} MiB/s")
    print(f"Min Throughput:     {min(throughputs):.2f} MiB/s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(main())

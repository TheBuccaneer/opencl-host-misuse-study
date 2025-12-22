
#include <iostream>
#include <vector>
#include <CL/cl.hpp>
#include "CASLibWrapper.h"

const char* kernelSource = R"(
__kernel void process_image(
    __global uchar* input,
    __global uchar* output,
    uint width,
    uint height
) {
    size_t x = get_global_id(0);
    size_t y = get_global_id(1);
    if (x >= width || y >= height) return;
    size_t idx = (y * width + x) * 4;
    output[idx + 0] = input[idx + 0];
    output[idx + 1] = input[idx + 1];
    output[idx + 2] = input[idx + 2];
    output[idx + 3] = input[idx + 3];
}
)";

int main() {
    std::cout << "=== OpenCL CAS Test ===" << std::endl;
    
    try {
        // Get platform and device
        std::vector<cl::Platform> platforms;
        cl::Platform::get(&platforms);
        
        if (platforms.empty()) {
            std::cerr << "No OpenCL platforms!" << std::endl;
            return 1;
        }
        
        std::vector<cl::Device> devices;
        platforms[0].getDevices(CL_DEVICE_TYPE_ALL, &devices);
        
        if (devices.empty()) {
            std::cerr << "No OpenCL devices!" << std::endl;
            return 1;
        }
        
        cl::Context context(devices[0]);
        cl::CommandQueue queue(context, devices[0]);
        
        std::cout << "✓ Platform: " << platforms[0].getInfo<CL_PLATFORM_NAME>() << std::endl;
        std::cout << "✓ Device: " << devices[0].getInfo<CL_DEVICE_NAME>() << std::endl;
        
        // Build program
        cl::Program program(context, kernelSource);
        if (program.build({devices[0]}) != CL_SUCCESS) {
            std::cerr << "Build failed!" << std::endl;
            return 1;
        }
        std::cout << "✓ Program built" << std::endl;
        
        // Create kernel
        cl::Kernel kernel(program, "process_image");
        
        // Test 1: Normal execution
        std::cout << "\n[TEST 1] Normal Kernel Execution" << std::endl;
        uint32_t w = 512, h = 512;
        uint32_t size = w * h * 4;
        
        std::vector<unsigned char> input(size, 128);
        std::vector<unsigned char> output(size, 0);
        
        cl::Buffer in_buf(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, size, input.data());
        cl::Buffer out_buf(context, CL_MEM_WRITE_ONLY, size);
        
        kernel.setArg(0, in_buf);
        kernel.setArg(1, out_buf);
        kernel.setArg(2, w);
        kernel.setArg(3, h);
        
        queue.enqueueNDRangeKernel(kernel, cl::NullRange, cl::NDRange(w, h), cl::NDRange(16, 16));
        queue.finish();
        std::cout << "✓ Kernel executed successfully" << std::endl;
        
        // Test 2: Misuse - invalid work group size
        std::cout << "\n[TEST 2] Invalid Work Group Size (Misuse)" << std::endl;
        try {
            queue.enqueueNDRangeKernel(kernel, cl::NullRange, cl::NDRange(w, h), cl::NDRange(1024, 1024));
            queue.finish();
            std::cout << "❌ Should have failed but didn't!" << std::endl;
        }
        catch (const cl::Error& e) {
            std::cout << "✓ Caught error (expected): " << e.what() << " Code: " << e.err() << std::endl;
        }
        
        // Test 3: CAS Integration
        std::cout << "\n[TEST 3] CAS-2D Integration" << std::endl;
        void* cas = CAS_initialize();
        if (cas) {
            std::cout << "✓ CAS initialized" << std::endl;
            CAS_destroy(cas);
            std::cout << "✓ CAS destroyed" << std::endl;
        }
        
        return 0;
    }
    catch (const cl::Error& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
EOF

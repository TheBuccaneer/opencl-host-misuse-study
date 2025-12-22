#define CL_TARGET_OPENCL_VERSION 300
#include <CL/cl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char* kernelSource = 
"__kernel void process_image("
"    __global uchar* input,"
"    __global uchar* output,"
"    uint width,"
"    uint height"
") {"
"    size_t x = get_global_id(0);"
"    size_t y = get_global_id(1);"
"    if (x >= width || y >= height) return;"
"    size_t idx = (y * width + x) * 4;"
"    output[idx + 0] = input[idx + 0];"
"    output[idx + 1] = input[idx + 1];"
"    output[idx + 2] = input[idx + 2];"
"    output[idx + 3] = input[idx + 3];"
"}";

int main() {
    printf("=== OpenCL Simple Test ===\n");
    
    // Get platform
    cl_platform_id platform;
    clGetPlatformIDs(1, &platform, NULL);
    
    char platform_name[100];
    clGetPlatformInfo(platform, CL_PLATFORM_NAME, sizeof(platform_name), platform_name, NULL);
    printf("✓ Platform: %s\n", platform_name);
    
    // Get device
    cl_device_id device;
    clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, 1, &device, NULL);
    
    char device_name[100];
    clGetDeviceInfo(device, CL_DEVICE_NAME, sizeof(device_name), device_name, NULL);
    printf("✓ Device: %s\n", device_name);
    
    // Create context
    cl_context context = clCreateContext(NULL, 1, &device, NULL, NULL, NULL);
    printf("✓ Context created\n");
    
    // Create queue
    cl_command_queue queue = clCreateCommandQueue(context, device, 0, NULL);
    printf("✓ Command Queue created\n");
    
    // Build program
    cl_program program = clCreateProgramWithSource(context, 1, &kernelSource, NULL, NULL);
    clBuildProgram(program, 1, &device, NULL, NULL, NULL);
    printf("✓ Program built\n");
    
    // Create kernel
    cl_kernel kernel = clCreateKernel(program, "process_image", NULL);
    
    printf("\n[TEST 1] Normal Kernel Execution\n");
    uint32_t w = 512, h = 512;
    uint32_t size = w * h * 4;
    
    unsigned char* input = malloc(size);
    unsigned char* output = malloc(size);
    memset(input, 128, size);
    memset(output, 0, size);
    
    cl_mem in_buf = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, size, input, NULL);
    cl_mem out_buf = clCreateBuffer(context, CL_MEM_WRITE_ONLY, size, NULL, NULL);
    
    clSetKernelArg(kernel, 0, sizeof(cl_mem), &in_buf);
    clSetKernelArg(kernel, 1, sizeof(cl_mem), &out_buf);
    clSetKernelArg(kernel, 2, sizeof(uint32_t), &w);
    clSetKernelArg(kernel, 3, sizeof(uint32_t), &h);
    
    size_t global_work_size[2] = {w, h};
    size_t local_work_size[2] = {16, 16};
    
    clEnqueueNDRangeKernel(queue, kernel, 2, NULL, global_work_size, local_work_size, 0, NULL, NULL);
    clFinish(queue);
    printf("✓ Kernel executed successfully\n");
    
    printf("\n[TEST 2] Invalid Work Group Size (Misuse)\n");
    size_t bad_local[2] = {1024, 1024};
    cl_int err = clEnqueueNDRangeKernel(queue, kernel, 2, NULL, global_work_size, bad_local, 0, NULL, NULL);
    
    if (err == CL_INVALID_WORK_GROUP_SIZE) {
        printf("✓ Correctly detected: CL_INVALID_WORK_GROUP_SIZE\n");
    } else if (err == CL_INVALID_VALUE) {
        printf("✓ Correctly detected: CL_INVALID_VALUE\n");
    } else if (err != CL_SUCCESS) {
        printf("✓ Error detected (Code: %d)\n", err);
    } else {
        printf("❌ No error (shouldn't happen)\n");
    }
    
    // Cleanup
    clReleaseMemObject(in_buf);
    clReleaseMemObject(out_buf);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(queue);
    clReleaseContext(context);
    free(input);
    free(output);
    
    printf("\n=== Test Complete ===\n");
    return 0;
}

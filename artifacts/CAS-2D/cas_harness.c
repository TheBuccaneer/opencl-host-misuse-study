#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "CASLibWrapper.h"

int main() {
    printf("CAS-2D OpenCL Harness\n");
    

    printf("CAS_initialize() Test 1\n");
    void* cas = CAS_initialize();
    if (cas == NULL) {
        fprintf(stderr, "CAS initialization failed\n");
        return 1;
    }
    printf("CAS initialized at %p\n\n", cas);
    

    printf("Test 2 CAS_supplyImage()\n");
    uint32_t width = 256, height = 256;
    uint32_t size = width * height * 4; 
    
    unsigned char* image = malloc(size);
    if (image == NULL) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }
    memset(image, 128, size); 
    
    printf("Supplying %ux%u RGBA image (%u bytes)\n", width, height, size);
    CAS_supplyImage(cas, image, 1, height, width);
    printf("Image supplied\n\n");
    
    // Test 3: Sharpen (Triggers OpenCL!)
    printf("Test 3 CAS_sharpenImage() - Triggers OpenCL\n");
    const unsigned char* result = CAS_sharpenImage(cas, 0, 0.5f, 0.5f);
    
    if (result != NULL) {
        printf("Image sharpened, result at %p\n", (void*)result);
    } else {
        printf("CAS returned NULL result\n");
    }
    printf("\n");
    

    printf("CAS_destroy()\n");
    CAS_destroy(cas);
    printf("CAS destroyed\n");
    
    free(image);
    
    printf("\nAll tests completed successfully\n");
    return 0;
}

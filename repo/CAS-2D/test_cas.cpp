#include <iostream>
#include "CASLibWrapper.h"

int main() {
    std::cout << "=== CAS-2D Test Program ===" << std::endl;
    
    // Initialize CAS
    void* cas = CAS_initialize();
    if (cas == nullptr) {
        std::cerr << "CAS initialization failed!" << std::endl;
        return 1;
    }
    std::cout << "CAS initialized: " << cas << std::endl;
    
    // Simulate a misuse: Double destroy (Use-After-Free pattern)
    std::cout << "Calling CAS_destroy()" << std::endl;
    CAS_destroy(cas);
    
    std::cout << "Calling CAS_destroy() AGAIN (Misuse!)" << std::endl;
    CAS_destroy(cas);  // ← MISUSE: Use-After-Free
    
    std::cout << "=== Test finished ===" << std::endl;
    return 0;
}

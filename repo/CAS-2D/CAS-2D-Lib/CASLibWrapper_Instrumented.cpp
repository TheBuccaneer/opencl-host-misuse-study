#include "include/CASLibWrapper.h"
#include <exception>
#if defined (_USE_OPENCL_)
#include "CASImpl.hpp"
#endif
//Implementation of the CAS DLL API - INSTRUMENTED FOR MISUSE TESTING
extern "C" {

    CAS_API void* CAS_initialize()
    {
        try {
            return new CASImpl();
        }
        catch (const std::exception&) {
            return nullptr;
        }
    }

    CAS_API void CAS_supplyImage(void* casImpl, const unsigned char* inputImage, const int hasAlpha, const unsigned int rows, const unsigned int cols)
    {
        // MISUSE #1: NULL pointer dereference
        // if (casImpl == nullptr) {
        //     std::cerr << "ERROR: casImpl is nullptr!" << std::endl;
        // }
        
        CASImpl* cas = static_cast<CASImpl*>(casImpl);
        cas->reinitializeMemory(hasAlpha, inputImage, rows, cols);
    }

    CAS_API const unsigned char* CAS_sharpenImage(void* casImpl, const int casMode, const float sharpenStrength, const float contrastAdaption)
    {
        // MISUSE #2: Invalid buffer access
        // if (sharpenStrength < 0.0f || sharpenStrength > 1.0f) {
        //     // Oclgrind might catch invalid kernel parameters here
        // }
        
        CASImpl* cas = static_cast<CASImpl*>(casImpl);
        return cas->sharpenImage(casMode, sharpenStrength, contrastAdaption);
    }

    CAS_API void CAS_destroy(void* casImpl)
    {
        // MISUSE #3: Use-After-Free (double destroy)
        // This segfaults in C++ but NOT detectable by Oclgrind
        // It's a CTSA-unreachable misuse (only detectable by ASan/Valgrind)
        
        CASImpl* cas = static_cast<CASImpl*>(casImpl);
        delete cas;
    }
}

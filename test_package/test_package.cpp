#include <iostream>

extern "C" {
#include <xed/xed-interface.h>
}

int main() {
    std::cout << "XED loaded version: " << xed_get_version() << std::endl;
    return 0;
}

/* BEGIN_LEGAL 

Copyright (c) 2026 Intel Corporation

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
  
END_LEGAL */
/// @file xed-test-api-check.c
/// @brief Tests api_check() abort behavior using subprocess pattern.

#include "xed/xed-interface.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#  include <process.h>
#else
#  include <sys/types.h>
#  include <sys/wait.h>
#  include <unistd.h>
#endif

int main(int argc, char** argv);

// Runs test in subprocess. Returns 1 for any nonzero exit (abort, or
// exec/spawn failure); 0 only if the child ran and exited with status 0.
static xed_int_t aborted(const char* executable, const char* option) {
#if defined(_WIN32)
    const char* arguments[3];
    intptr_t status;

    arguments[0] = executable;
    arguments[1] = option;
    arguments[2] = 0;
    status = _spawnv(_P_WAIT, executable, arguments);
    return status != 0;
#else
    char* arguments[3];
    pid_t child;
    xed_int_t status;

    arguments[0] = (char*) executable;
    arguments[1] = (char*) option;
    arguments[2] = 0;
    child = fork();
    if (child == 0) {
        execv(executable, arguments);
        _exit(127);
    }
    if (child < 0 || waitpid(child, &status, 0) < 0) {
        return 1;
    }
    return !WIFEXITED(status) || WEXITSTATUS(status) != 0;
#endif
}

int main(int argc, char** argv) {
    xed_int_t passed = 0, failed = 0;
    xed_int_t invalid_aborted;

    if (argc >= 2 && strcmp(argv[1], "--invalid") == 0) {   
        api_check(0);
        return 0;
    }

    if (argc >= 2 && strcmp(argv[1], "--valid") == 0) {     
        api_check(1);
        return 0;
    }

    invalid_aborted = aborted(argv[0], "--invalid");
    
#if defined(XED_API_CHECK_ENABLED)
    printf("Testing with XED_API_CHECK_ENABLED=1\n");
    if (invalid_aborted) {
        printf("PASS: api_check(0) aborted\n");
        passed++;
    } else {
        printf("FAIL: api_check(0) did not abort\n");
        failed++;
    }
#else
    printf("Testing with XED_API_CHECK_ENABLED=0 (disabled)\n");
    if (!invalid_aborted) {
        printf("PASS: api_check(0) survived (no checking)\n");
        passed++;
    } else {
        printf("FAIL: api_check(0) aborted (unexpected)\n");
        failed++;
    }
#endif
    
    if (!aborted(argv[0], "--valid")) {
        printf("PASS: api_check(1) survived\n");
        passed++;
    } else {
        printf("FAIL: api_check(1) aborted\n");
        failed++;
    }
    
    printf("%d passed, %d failed\n", passed, failed);
    return (failed > 0) ? 1 : 0;
}

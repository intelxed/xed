/*BEGIN_LEGAL 

Copyright (c) 2018 Intel Corporation

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
//#define XED_PROFILE_TRAVERSAL
//#define XED_PROFILE_NODE_FREQUENCY
//#define XED_PROFILE_ITERATION_TIME



////////////////////////////////////////////////////////////////////////////

#if defined(XED_PROFILE_TRAVERSAL)
# define XED_MAX_ITERATIONS_PROFILE 100
xed_uint64_t xed_profile_iterations[XED_MAX_ITERATIONS_PROFILE];

# define BUMP_PROFILE()                   \
         do {                             \
            if (iterations < XED_MAX_ITERATIONS_PROFILE)    \
                xed_profile_iterations[iterations]++;\
            else \
                xed_profile_iterations[XED_MAX_ITERATIONS_PROFILE-1]++; \
        } while(0)

#else
# define BUMP_PROFILE()  do {} while(0)
#endif

////////////////////////////////////////////////////////////////////////////

#if defined(XED_PROFILE_NODE_FREQUENCY)
xed_uint64_t xed_profile_node_frequency[XED_GRAPH_NODE_LAST];
#endif



#if defined(XED_PROFILE_ITERATION_TIME)
xed_uint64_t times[1000];
xed_uint32_t xed_decode_traversals=0; 
#endif


#if !defined(__GNUC__)
# pragma warning( default : 4706)
#endif


#if defined(XED_PROFILE_ITERATION_TIME)
void xed_decode_traverse_iteration_times(void) {
    int i;
    xed_uint64_t last=0;
    printf("TRAVERSALS: " XED_FMT_D "\n", xed_decode_traversals);

    for(i=0;i<xed_decode_traversals;i++) {
        //if (times[i] == 0)
        //    break;
        printf("%d ", i);
        printf(XED_FMT_LD " ", times[i]);
        if (last)
            printf(XED_FMT_LD, times[i]-last);
        printf("\n");
        last = times[i];
    }
}
#endif

void xed_decode_traverse_dump_profile(void) 
{
#if defined(XED_PROFILE_ITERATION_TIME)
    xed_decode_traverse_iteration_times();
#endif

#if defined(XED_PROFILE_TRAVERSAL)
    int i;
    for(i=0;i<XED_MAX_ITERATIONS_PROFILE;i++) 
        if (xed_profile_iterations[i])
            XED2IMSG((xed_log_file, "DECTRAV PROFILE " XED_FMT_D 
                      " " XED_FMT_LD "\n", 
                      i, xed_profile_iterations[i]));
#endif
}

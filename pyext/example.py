#BEGIN_LEGAL
#
#Copyright (c) 2021 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#  
#END_LEGAL
import xed
print(xed.dis32([0,0]))
print(xed.dis64([0x48,0,0]))
print(xed.dis32([0x67, 0x8b, 0x46, 0xff]))
print(xed.dis32([0x75, 0x10]))
print(xed.dis64([0x75, 0x10], 0xaaaabbbffff0000))


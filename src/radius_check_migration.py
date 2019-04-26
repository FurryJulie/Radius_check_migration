#!/usr/bin/env python3

'''
Author: Julie Daligaud <julie.daligaud@gmail.com>

Copyright 2019 Julie Daligaud.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import sys
import time
import subprocess
import progressbar


BAR = progressbar.ProgressBar(max_value=progressbar.UnknownLength, redirect_stdout=False)

def usage():
    message = "Usage: " \
              + sys.argv[0] \
              + " radius_users_file radius_ip radius_port radius_secret" \
              + "radius_ip radius_port radius_secret"

    if len(sys.argv) != 8:
        print(message)
        sys.exit(1)

def get_file_content(file_path):
    content = None

    with open(file_path, "r") as f:
        content = f.read()
        f.close()

    return content

def clear_radius_user_line(user_line):
    cleared_line = []

    for c in user_line:
        if '\t' in c:
            tmp = c.split('\t')
            for d in tmp:
                if len(str(d)) > 0:
                    cleared_line.append(str(d))
        else:
            if len(c) > 0:
                cleared_line.append(str(c))

    return cleared_line


def get_radius_users_from_file(users_file_path):
    users_file = get_file_content(users_file_path)

    if not users_file or len(users_file) <= 0:
        print("Users file is empty.")
        sys.exit(1)

    users = {}
    cpt = 0
    users_temp = users_file.split("\n")
    for line in users_temp:
        if "Cleartext-Password" in line:
            user_line = str(line.strip()).split(" ")
            user_line = clear_radius_user_line(user_line)
            users[str(user_line[0]).strip()] = \
                str(str(user_line[3]).strip()).strip('"')

    return users


def test_server_connectivity(ip, retry):
    tries = 0
    connectivity_ok = False

    while tries <= retry:
        tries +=1
        try:
            output = subprocess.check_output(["/bin/ping", "-W", "3", "-c", "1", str(ip)], timeout=5 )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            time.sleep(1)
            continue
        else:
            if not output or len(str(output)) <= 0 \
              or "Destination Net Unreachable" in str(output) \
              or "No route to host" in str(output) \
              or "0 received" in str(output) :
                time.sleep(1)
                continue
            else:
                connectivity_ok = True
                break


    if not connectivity_ok:
        print("Error : " + ip + " Radius server unreachable.")
        sys.exit(1)

def radtest(users, rad_ip, rad_port, rad_secret, tout, retry):
    '''
    Call radtest as a shell subprocess, verify its return code
    and store the output.

    users: (MAP<str, str>) Map of <user, pwd> which to perform radtest
    rad_ip: (str) IP of the Radius server
    rad_port: (str) Port of the Radius Server
    rad_secret: (str) Secret of the Radius Server (see /ect/freeradius/3.0/clients.conf)
    tout: (int) Timeout of radtest
    retry: (int) Number of retries to perform for each user

    returns a MAP<str, str> of user and output of radtest.
    '''

    test_server_connectivity(rad_ip, 5)

    radtest_output = {}
    found_users = 0

    for user, pwd in users.items():
        found = False
        tries = 0
        while tries <= retry:
            tries += 1
            try:
                output = subprocess.check_output(["/usr/bin/radtest", "-4", str(user), str(pwd), str(rad_ip), str(rad_port), str(rad_secret)], timeout=tout)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                time.sleep(0.07)
                continue
            else:
                radtest_output[str(user)] = str(output)
                found = True
                found_users += 1
                BAR.update(found_users)
                break
        if not found:
                print("User: " + str(user) + " pwd: " + str(pwd) + " radtest returned an error.")
                sys.exit(1)
        time.sleep(0.07)

    return radtest_output

def check_rad_replies(radtest_output1, radtest_output2, ip1, ip2):
    '''
    Check if radius replies are the same for the 2 servers.
    '''

    if len(radtest_output1.keys()) != len(radtest_output2.keys()):
        print("Output from server 1 and server 2 arent the same.")
        sys.exit(1)

    error = False

    for user, out1 in radtest_output1.items():
        if str(user) not in radtest_output2.keys():
            print("Error for user " + str(user))
            error = True
            continue

        # Verify if outputs are exactly the same
        if out1 == radtest_output2[str(user)]:
            continue
        else:
            user_output1 = str(out1).split("\\n")
            user_output2 = str(str(radtest_output2[str(user)]).strip()).split("\\n")

            if len(user_output1) != len(user_output2):
                print("Error for user " + str(user))
                error = True
                continue

            ver = 0
            for string in user_output1:
                ver += 1
                if str(ip1) in str(string) or str(ip2) in str(string):
                    continue
                else:
                    if str(string).strip() not in user_output2:
                        print("Error for user " + str(user))
                        error = True
                        break

        if error:
            print("Error found for user : " + str(user))
            sys.exit(1)

    if not error:
        print("Checked " + str(len(radtest_output1.keys())) + " entries. OK.")
    else:
        print("Error found.")


def main():
    usage()
    # get all users from the users file and parse them into a user-password array

    users = get_radius_users_from_file(str(sys.argv[1]).strip())
    BAR = progressbar.ProgressBar(max_value=progressbar.UnknownLength, redirect_stdout=False)
    BAR.update(0)
    out1 = radtest(users, str(sys.argv[2]), str(sys.argv[3]), str(sys.argv[4]), 5, 1)
    BAR = progressbar.ProgressBar(max_value=progressbar.UnknownLength, redirect_stdout=False)
    BAR.update(0)
    out2 = radtest(users, str(sys.argv[5]), str(sys.argv[6]), str(sys.argv[7]), 5, 1)
    check_rad_replies(out1, out2, str(sys.argv[2]), str(sys.argv[5]))


if __name__ == "__main__":
    main()

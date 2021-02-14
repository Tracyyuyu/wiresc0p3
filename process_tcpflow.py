#!/usr/bin/env python

import os
import re

# list all the server ports that we want to watch
watch_ports = ['8090']

curr_dir = os.path.dirname(os.path.realpath(__file__))
flow_root_dir = f'{curr_dir}/out/tcpflow'


def construct_response_file_name(fname):
    fname_segments = fname.split("-")
    opt_suffix = ''
    # handle cases where the file name contains suffixes like c1, c2, etc
    if 'c' in fname_segments[1]:
        split_suffix = fname_segments[1].split('c')
        fname_segments[1] = split_suffix[0]
        opt_suffix = 'c' + split_suffix[1]
    resp_file_name = f'{fname_segments[1]}-{fname_segments[0]}{opt_suffix}'
    return resp_file_name


def extract_port_numbers(file_name):
    file_name_segments = file_name.split("-")
    from_port = int(file_name_segments[0][len(file_name_segments[0]) - 5:])
    if 'c' in file_name_segments[1]:
        file_name_segments[1] = file_name_segments[1].split('c')[0]
    to_port = int(file_name_segments[1][len(file_name_segments[1]) - 5:])
    return from_port, to_port


def process_request_file(root_dir, file_name):
    fq_file_name = os.path.join(root_dir, file_name)
    print(f'processing request file: {fq_file_name}')
    http_requests = []
    with open(fq_file_name, 'r') as f:
        content = f.read()
        lines = content.splitlines()
        req_body = ''
        for line in lines:
            # append new requests to the end of the list
            req_idx = len(http_requests) - 1
            if len(line) > 0:
                http_header_matches = re.finditer("(GET|HEAD|POST|PUT|DELETE) /", line)
                http_header_found = False
                header_found_index = 0
                # request line which contains the http method marks the beginning of the request
                for http_header_match in http_header_matches:
                    http_header_found = True
                    header_found_index = http_header_match.start(0)
                if http_header_found:
                    # handle requests where http method is not at index 0 of line
                    if header_found_index > 0:
                        req_body = line[:header_found_index]
                        http_requests.append({'request': line[header_found_index:]})
                    else:
                        http_requests.append({'request': line})
                else:
                    req_body = line
            if ':' in req_body:
                http_requests[req_idx]['headers'] = req_body
            else:
                http_requests[req_idx]['payload'] = req_body
    return http_requests


def process_response_file(root_dir, file_name):
    fq_file_name = os.path.join(root_dir, file_name)
    print(f'processing response file {fq_file_name}...')
    http_responses = []
    if not fq_file_name.endswith('.html'):
        with open(fq_file_name, 'rb') as f:
            content = f.read()
            lines = content.splitlines()
            for line in lines:
                res_idx = len(http_responses) - 1
                try:
                    str_line = line.decode()
                    if 'HTTP/1.1' in str_line:
                        idx = str_line.index('HTTP/1.1')
                        if idx > 0:
                            http_responses[res_idx]['response_headers'] += str_line[:idx]
                        http_responses.append(
                            {'response_code': str_line[idx:], 'response_headers': '', 'response_bytes': ''})
                    else:
                        http_responses[res_idx]['response_headers'] += str_line
                except UnicodeDecodeError as ude:
                    if b'HTTP/1.1' in line:
                        idx = line.index(b'HTTP/1.1')
                        if idx > 0:
                            http_responses[res_idx]['response_bytes'] += str(line[:idx])
                        http_responses.append(
                            {'response_code': line[idx:].decode(), 'response_headers': '', 'response_bytes': ''})
                    else:
                        http_responses[res_idx]['response_bytes'] += str(line)
    return http_responses


def extract_http_interaction(root_dir, file_name):
    fq_filename = os.path.join(root_dir, file_name)
    filtered_ports = [port for port in watch_ports if (port in fq_filename)]
    if len(filtered_ports) > 0:
        from_port, to_port = extract_port_numbers(file_name)
        if str(from_port) in watch_ports:
            responses = process_response_file(root_dir, file_name)
            for resp in responses:
                print(resp)
        if str(to_port) in watch_ports:
            reqs = process_request_file(root_dir, file_name)
            for req in reqs:
                print(req)


def main():
    for root_dir, dirs, files in os.walk(flow_root_dir):
        for file_name in files:
            extract_http_interaction(root_dir, file_name)


if __name__ == '__main__':
    main()

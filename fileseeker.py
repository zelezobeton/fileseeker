#!/usr/bin/python3
"""
Author: Josef Adamek
Python version: 3.10

Show help with these commands:
    python3 fileseeker.py -h
    python3 fileseeker.py scan/detect -h

Program stores metadata of files with scan command,
then with detect command figures how the files has been changed.
"""
import argparse
import os
import json
import copy
import hashlib
import asyncio
import logging

def scan(directories, result_fp):
    """
    Scan input directories for metadata and save them to JSON file
    """
    directories_dict = dict()
    # Loop through input directories
    for directory in directories:
        if not os.path.isdir(directory):
            logging.error(f'Input directory {directory} is invalid')
            continue 

        directories_dict[directory] = dict()
        # Recursively walk through input directory
        for (dirpath, _dirnames, filenames) in os.walk(directory):
            directories_dict[directory][dirpath] = dict()
            # Loop through filenames and get their hash
            for filename in filenames:
                with open(os.path.join(dirpath, filename), 'r') as f:
                    string_hash = hashlib.sha256(f.read().encode('utf-8')).hexdigest()
                directories_dict[directory][dirpath][filename] = string_hash
                logging.debug(f'File {filename} was scanned with hash {string_hash}')
            logging.debug(f'Directory {dirpath} was scanned')
        logging.debug(f'Input directory {dirpath} was scanned')            
    
    # Save result in JSON format
    with open(result_fp, 'w') as f:
        json.dump(directories_dict, f, indent=4)
        logging.info(f'Scan result was saved in JSON format on path {result_fp}')      

def detect_files(filenames, directory, scan_result_copy, directory_path, directory_path2):
    """
    Go through files from current file structure and detect changes done to files
    """
    filenames_current = []
    # Loop through filenames in current state of directory structure
    for filename in filenames:
        filenames_current.append(filename)
        # File stays
        if filename in directory[directory_path2]:
            with open(os.path.join(directory_path2, filename), 'r') as f:
                string_hash = hashlib.sha256(f.read().encode('utf-8')).hexdigest()
            # File unmodified
            if string_hash == directory[directory_path2][filename]:
                scan_result_copy[directory_path][directory_path2][filename] = "UNMODIFIED"
                logging.debug(f"File {filename} is unmodified")
            # File modified
            else:
                scan_result_copy[directory_path][directory_path2][filename] = "MODIFIED"
                logging.debug(f"File {filename} was modified")
        # File added
        else:
            scan_result_copy[directory_path][directory_path2][filename] = "ADDED"
            logging.debug(f"File {filename} was added")
    
    # Loop through filenames from scan result
    for filename, _string_hash in directory[directory_path2].items():
        # File deleted
        if filename not in filenames_current:
            scan_result_copy[directory_path][directory_path2][filename] = "DELETED"
            logging.debug(f"File {filename} was deleted")

def detect(scan_result_fp, result_fp):
    """
    Go through scan result and current state of file structure, compare it,
    and save results to JSON file
    """
    # Check if scan result path is valid
    if not os.path.isfile(scan_result_fp):
        logging.error(f'Input scan result filepath {scan_result_fp} is invalid')
        return

    # Read scan result
    with open(scan_result_fp, 'r') as f:
        scan_result = json.load(f)
        logging.info(f"Scan result was read")
    
    scan_result_copy = copy.deepcopy(scan_result)
    # Loop through input directories in scan result
    for directory_path, directory in scan_result.items():
        dirpaths_current = []
        # Recursively walk through current state of directory structure
        for directory_path2, _dirnames, filenames in os.walk(directory_path):
            dirpaths_current.append(directory_path2)

            # Directory not changed
            if directory_path2 in directory:
                detect_files(filenames, directory, scan_result_copy, directory_path, directory_path2)
                logging.debug(f"Directory {directory_path2} was not changed")

            # Directory added
            else:
                scan_result_copy[directory_path][directory_path2] = dict()
                for filename in filenames:
                    scan_result_copy[directory_path][directory_path2][filename] = "ADDED"
                logging.debug(f"Directory {directory_path2} was added")
        
        # Loop through directories from scan result
        for directory_path2, directory2 in directory.items():
            # Directory deleted
            if directory_path2 not in dirpaths_current:
                for filename in directory2:
                    scan_result_copy[directory_path][directory_path2][filename] = "DELETED"
                logging.debug(f"Directory {directory_path2} was deleted")
    
    # Save result in JSON format
    with open(result_fp, 'w') as f:
        json.dump(scan_result_copy, f, indent=4)
        logging.info(f'Detect result was saved in JSON format on path {result_fp}')

async def scan_async(directories, result_fp):
    """
    Run scan command asynchronously
    """
    scan(directories, result_fp)

async def detect_async(scan_result_fp, result_fp):
    """
    Run detect command asynchronously
    """
    detect(scan_result_fp, result_fp)

def parse_args():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(
                    prog='FileSeeker',
                    description='Program stores metadata of files with scan command, '
                                'then with detect command figures how the files has been changed')
    parser.add_argument('-a', '--asyncio', action='store_true', help='Run commands asynchronously')
    parser.add_argument('-ll', '--log_level', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help='Choose logging level')
    parser.add_argument('-lf', '--log_file', help='Choose log file destination')
    subparsers = parser.add_subparsers(help='Mode in which program will be run', dest='command')
    
    scan_parser = subparsers.add_parser('scan', help='Scan files metadata')
    scan_parser.add_argument('directories', nargs='+', help='Directories which will be scanned')
    scan_parser.add_argument('-r', '--result', help='Output result file', required=True)
    
    detect_parser = subparsers.add_parser('detect', help='Detect changes of files')
    detect_parser.add_argument('-sr', '--scan_result', help='Input scan result file', required=True)
    detect_parser.add_argument('-r', '--result', help='Output result file', required=True)
    return parser.parse_args()

def main():
    """
    Run commands based on command line arguments
    """
    args = parse_args()

    # Configure logging
    level = None
    if args.log_level is not None:
        level = getattr(logging, args.log_level)
    logging.basicConfig(filename=args.log_file, filemode='w', level=level)

    # Choose command and if it will be run asynchronously
    if args.command == "scan":
        if args.asyncio:
            asyncio.run(scan_async(args.directories, args.result))
        else:
            scan(args.directories, args.result)
    elif args.command == "detect":
        if args.asyncio:
            asyncio.run(detect_async(args.scan_result, args.result))
        else:
            detect(args.scan_result, args.result)

if __name__ == "__main__":
    main()
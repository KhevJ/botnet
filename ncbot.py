#!/bin/env python3

import argparse
import select
import socket
import time
import hashlib

HOST = None
PORT = None
NICK = None
SECRET = None
no_of_commands = 0
seen_nonces = set()

def parse_args():
    '''
    parsing of inputs logic 
    needs the hostport, nickname and secret
    '''
    parser = argparse.ArgumentParser(
        prog='client',
        description='client connects to server')
    parser.add_argument("hostport", help="<hostname>:<port>")
    parser.add_argument("nick", help="Nickname for the bot")
    parser.add_argument("secret", help="Secret key for authentication")
    return parser.parse_args()

def move(sock, cmd):
    '''
    handles move logic
    we are essentially re-doing the connection logic by re-calling socket_connection
    but with a different host and port
    '''
    global HOST, PORT, NICK
    HOST, PORT = cmd[1].split(":")
    PORT = int(PORT)
    sock.sendall(f"-move {NICK} \n".encode())
    time.sleep(1) 
    sock.shutdown(socket.SHUT_RDWR)
    sock.close() # closing connection
    socket_connection() # creating new connection with new hosts or ports
    
    
def attack(sock, cmd, nonce):
    '''
    handles attack logic 
    a new socket connection to the given host:port is created
    and an "attack" is sent
    whether an error happens or it is successfull a message is sent
    '''
    global NICK
    host, port = cmd[1].split(":")
    port = int(port)
    try:
        with socket.create_connection((host,port), timeout=3) as s:
            s.sendall(f"{NICK} {nonce} \n".encode())
            time.sleep(0.5)
            sock.sendall(f"-attack {NICK} OK \n".encode())
            s.shutdown(socket.SHUT_RDWR)
            s.close()
    # handling of errors
    except TimeoutError: #if attack is not done within 3 s
        sock.sendall(f"-attack {NICK} FAIL timeout \n".encode())
        
    except socket.gaierror as e: #if hostname is not valid
        sock.sendall(f"-attack {NICK} FAIL no such hostname \n".encode())
            
    except ConnectionRefusedError: # hostname is not running 
        sock.sendall(f"-attack {NICK} FAIL connection refused \n".encode())
        
    except Exception as e: # other errors
        sock.sendall(f"-attack {NICK} FAIL {e} \n".encode())
    

def handle_command(sock, cmd):
    '''
    handles every  command that the bot has to support
    status, move, attack, shutdown
    
    '''
    global HOST, PORT, NICK, SECRET, no_of_commands # no_of_commands will count the number of times a valid command is called used for status
    #print(cmd)
    nonce = cmd[0]
    cmd = cmd[2:]
    if cmd[0] == "status":
        if(len(cmd) != 1): 
            print("Invalid usage of status, needs 3 args including nonce and mac")
            return 
        no_of_commands += 1
        sock.sendall(f"-status {NICK} {no_of_commands}\n".encode()) #send back to server
        
    elif cmd[0] == "attack":
        if(len(cmd) != 2): 
            print("Invalid usage of attack, needs 4 args including nonce and mac")
            return #not args = <attack> <hostname:port>
        no_of_commands += 1
        attack(sock, cmd, nonce)
        
    elif cmd[0] == "move":
        if(len(cmd) != 2): 
            print("Invalid usage of move, needs 4 args including nonce and mac")
            return #not args = <move> <hostname:port>
        no_of_commands += 1
        move(sock, cmd)
        
    elif cmd[0] == "shutdown":
        if(len(cmd) != 1): 
            print("Invalid usage of shutdown, needs 3 args including nonce and mac")
            return
        no_of_commands += 1
        sock.sendall(f"-shutdown {NICK}\n".encode())
        time.sleep(1) #gives some time to let message to be sent
        sock.shutdown(socket.SHUT_RDWR) 
        sock.close() 
        exit(0) 
        
    else:
        return  #ignore command
    
def authenticate(cmd):
    '''
    # 1.) if <nonce> is in seen_nonces: ignore command
    # 2.) compute mac2 = sha-256(<nonce>+<secret>)
    # 3.) if mac2 != <mac>: ignore command
    # 4.) insert <nonce> into seen_nonces
    # 5.) execute command
    '''
    global SECRET,seen_nonces
    nonce, mac = cmd[0],cmd[1]
    if nonce in seen_nonces: return False #checks if nonce has been used before
    mac2 = hashlib.sha256((nonce + SECRET).encode()).hexdigest()[:8] #calculate mac2 from nonce + SECRET using hash256 encdoing and returns first 8
    #print(mac2)
    if mac2 != mac : return False
    seen_nonces.add(nonce)
    return True
        
    
    


def socket_connection():
    '''
    This function allows the socket connection 
    and handles retry to reconnect whenever socket disconnects
    or encounters other issues in a 5s interval
    '''
    global HOST, PORT, NICK, SECRET
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.sendall(f"-joined {NICK} \n".encode()) #sending join message
            print("Connected.")
            
            while True:
                ready, _, _ = select.select([s], [], [], 1)
                if ready:
                    command = s.recv(4096).decode()
                    if not command:
                        raise Exception 
                    cmd = command.split()
                    if len(cmd) <= 2 : continue #ignore commands with at most 2 args
                    if cmd[0].strip().startswith("-"): continue #ignore commands sent from bots
                    #authenticate(cmd)
                    if(authenticate(cmd)): #compares mac values
                        handle_command(s,cmd)
        #handling of disconnects or failure to connect       
        except ConnectionRefusedError: #when server is not on
            s.close()
            print("Failed to connect.")
            time.sleep(5) #sleeps for 5s
            
        except socket.gaierror as e:
            print(f"no such hostname")   
            time.sleep(5)
            
        except Exception as e:  #when server is disconnected
            s.close()
            print("Disconnected")
            time.sleep(5)
    

def main():
    '''
    parsing of args and assigning values to global vars 
    are done in this function
    '''
    global HOST, PORT, NICK, SECRET 
    args = parse_args()
    try:
        HOST, PORT = args.hostport.split(":")
        PORT = int(PORT)
    except ValueError:
        print("Error: Invalid <hostname>:<port> format. Expected 'hostname:port'.")
        exit(1)
    NICK = args.nick
    SECRET = args.secret
    socket_connection() # connects sockets to server
    
    
   
            
        
    


if __name__ == "__main__":
    main()

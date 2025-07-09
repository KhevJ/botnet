#!/bin/env python3

import argparse
import random
import select
import socket
import time
import hashlib

HOST = None
PORT = None
NICK = None
CHANNEL = None
SECRET = None
no_of_commands = 0
seen_nonces = set()

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

def move(sock, cmd):
    '''
    handles move logic
    we are essentially re-doing the connection logic by re-calling socket_connection with IRC
    but with a different host, port and channel
    '''
    global HOST, PORT, NICK, CHANNEL
    HOST, PORT = cmd[1].split(":")
    PORT = int(PORT)
    sock.sendall(f"PRIVMSG #{CHANNEL} :-move {NICK} \n".encode())
    CHANNEL = cmd[2]
    time.sleep(1)
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    socket_connection()
    
    
def attack(sock, cmd, nonce):
    '''
    handles attack logic 
    a new socket connection to the given host:port is created
    and an "attack" is sent
    whether an error happens or it is successfull a message is sent
    '''
    global NICK, CHANNEL
    host, port = cmd[1].split(":")
    port = int(port)
    try:
        with socket.create_connection((host,port), timeout=3) as s: # create new socket to send attack
            s.sendall(f"{NICK} {nonce} \n".encode())
            sock.sendall(f"PRIVMSG #{CHANNEL} :-attack {NICK} OK \r\n".encode())
            time.sleep(0.5) # sleep to allow message to be sent
            time.sleep(5)
            s.shutdown(socket.SHUT_RDWR)
            s.close() # close the socket
    #handle errors
    except TimeoutError:
        sock.sendall(f"PRIVMSG #{CHANNEL} :-attack {NICK} FAIL timeout \r\n".encode())
        
    except socket.gaierror as e:
        sock.sendall(f"PRIVMSG #{CHANNEL} :-attack {NICK} FAIL no such hostname \r\n".encode())
            
    except ConnectionRefusedError:
        sock.sendall(f"PRIVMSG #{CHANNEL} :-attack {NICK} FAIL connection refused \r\n".encode())
        
    except Exception as e:
        sock.sendall(f"PRIVMSG #{CHANNEL} :-attack {NICK} FAIL {e} \r\n".encode())
    

def handle_command(sock:socket.socket, cmd):
    '''
    handles every  command that the bot has to support
    status, move, attack, shutdown
    
    '''
    global HOST, PORT, NICK, SECRET, CHANNEL,  no_of_commands # no_of_commands will count the number of times a valid command is called used for status
    #print(cmd)
    nonce = cmd[0]
    cmd = cmd[2:]
    if cmd[0] == "status":
        if(len(cmd) != 1): 
            print("Invalid usage of status, needs 3 args including nonce and mac")
            return
        no_of_commands += 1
        sock.sendall(f"PRIVMSG #{CHANNEL} :-status {NICK} {no_of_commands}\r\n".encode())
        
    elif cmd[0] == "attack":
        if(len(cmd) != 2): 
            print("Invalid usage of attack, needs 4 args including nonce and mac")
            return #not args = <attack> <hostname:port>
        no_of_commands += 1
        attack(sock, cmd, nonce)
        
    elif cmd[0] == "move":
        if(len(cmd) != 3): 
            print("Invalid usage of move, needs 4 args including nonce and mac")
            return
        no_of_commands += 1
        move(sock, cmd)
        
    elif cmd[0] == "shutdown":
        if(len(cmd) != 1): 
            print("Invalid usage of shutdown, needs 3 args including nonce and mac")
            return
        no_of_commands += 1
        sock.sendall(f"PRIVMSG #{CHANNEL} :-shutdown {NICK}\r\n".encode())
        time.sleep(1)
        sock.shutdown(socket.SHUT_RDWR)  # flush the socket before closing to make sure all data is sent
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
    mac2 = hashlib.sha256((nonce + SECRET).encode()).hexdigest()[:8]
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
    global HOST, PORT, NICK, SECRET, CHANNEL
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            
            nick_in_use = True
            while(nick_in_use):
                s.sendall(f"NICK {NICK} \r\n".encode()) #sets a nickname
                s.sendall(f"USER {NICK} * * {NICK} \r\n".encode()) #sets the user with its attribute
                s.sendall(f"JOIN #{CHANNEL}\r\n".encode()) #joins a channle
                recv = s.recv(4096).decode()
                # print(recv)
                if("433" in recv): #checks if 433 is there which means nickname is in use
                         NICK = "bot-"+ str(random.randint(10, 99))  # reset the nickname
                else:
                    nick_in_use = False
            print("Connected")
            while True:
                ready, _, _ = select.select([s], [], [], 1)
                if ready:
                    commands = s.recv(4096).decode()
                    if not commands:
                        raise Exception
                    #command is separated in an array
                    commands = commands.strip()
                    commands = commands.strip('\r')
                    commands = commands.split("\n")
                    for command in commands:
                        cmd = command.split()
                        if(cmd[0] == "PING"):
                            s.sendall(f"PONG {cmd[1]} \r\n".encode()) # makes sure that the bot stays alive
                        if(cmd[1] == "PRIVMSG" and len(cmd) >=5):
                            cmd = cmd[3:]
                            cmd[0] = cmd[0].lstrip(':')
                            if(authenticate(cmd)): # compare macs 
                                handle_command(s,cmd) #handle any comments
                            
                        
        #handling errors    
        except ConnectionRefusedError: #when server is not on
            s.close()
            print("Failed to connect.")
            time.sleep(5)
            
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
    global HOST, PORT, NICK, SECRET, CHANNEL
    args = parse_args()
    try:
        HOST, PORT = args.hostport.split(":")
        PORT = int(PORT)
    except ValueError:
        print("Error: Invalid <hostname>:<port> format. Expected 'hostname:port'.")
        exit(1)
    CHANNEL = args.channel
    SECRET = args.secret
    NICK = "bot-"+ str(random.randint(10, 99)) # assigning random names to the bot
    socket_connection()
    
    
   
            
        
    


if __name__ == "__main__":
    main()


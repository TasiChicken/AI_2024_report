import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import gym
import random
from collections import deque
import os
from tqdm import tqdm
from chessboard import chessboard

class replay_buffer():
    def __init__(self, capacity):
        self.capacity = capacity  # the size of the replay buffer
        self.memory = deque(maxlen=capacity)  # replay buffer itself

    def insert(self, state, action, reward, next_state, done):
        self.memory.append([state, action, reward, next_state, done])

    def sample(self, batch_size):
        batch = random.sample(self.memory, batch_size)
        observations, actions, rewards, next_observations, done = zip(*batch)
        return observations, actions, rewards, next_observations, done

class Net(nn.Module):
    def __init__(self, dem_states, num_actions, hidden_layer_size=50):
        super(Net, self).__init__()
        self.input_state = dem_states  # the dimension of state space
        self.num_actions = num_actions  # the dimension of action space
        self.fc1 = nn.Linear(self.input_state, 32)  # input layer
        self.fc2 = nn.Linear(32, hidden_layer_size)  # hidden layer
        self.fc3 = nn.Linear(hidden_layer_size, num_actions)  # output layer

    def forward(self, states):
        '''
        Forward the state to the neural network.
        
        Parameter:
            states: a batch size of states
        
        Return:
            q_values: a batch size of q_values
        '''
        x = F.relu(self.fc1(states))
        x = F.relu(self.fc2(x))
        q_values = self.fc3(x)
        return q_values

def board_state_to_ndarray(board, color):
    arr = np.ndarray(shape=(25,))
    my_chesses = board.state[color]
    oppo_chesses = board.state[1 - color]
    for i in range(25):
        if board.all_posi[i] in my_chesses:
            arr[i] = 1
        elif board.all_posi[i] in oppo_chesses:
            arr[i] = -1
        else:
            arr[i] = 0
    return arr

def action_chess_to_posi(chess):
    return (chess[0], chess[2], )

def action_to_index(board, action, color):
    add_posi = board.all_posi.index(action_chess_to_posi(action[0])) + 1
    move_from_posi = 0
    eat_posi = 0
    for removed in action[1]:
        if removed[2] == color:
            move_from_posi = board.all_posi.index(action_chess_to_posi(removed)) + 1
        else:
            eat_posi = board.all_posi.index(action_chess_to_posi(removed))
    return add_posi * (25 ** 2) + move_from_posi * 25 + eat_posi

def index_to_action(board, index, color):
    arr = [0] * 3
    for i in range(3):
        arr[2-i] = index % 25
        index = index // 25
    
    add = { board.all_posi[arr[0] - 1] + (color, ) }
    remove = {}
    if arr[1] > 0:
        remove.add(board.all_posi[arr[1] - 1] + (color, ))
    if arr[2] > 0:
        remove.add(board.all_posi[arr[2] - 1] + (1-color, ))
    return (add, remove, )

def eval_reward(state, action, board, color):
    if board.isWin():
        return 100
    if board.isLose():
        return -100
    
    reward = len(state[color]) - 4 #make module wants to keep chess alive
    for removed in action[1]:
        if removed[2] == 1-color:
            return reward + 10
    return reward

class Agent():
    DICT_PATH = "./RL.pt"

    def __init__(self, board, color, epsilon=0.05, learning_rate=0.0002, GAMMA=0.97, batch_size=32, capacity=10000):
        self.board = board
        self.color = color
        self.d_states = 24  # the number of states
        self.n_actions = 25**3  # the number of actions
        self.count = 0  # recording the number of iterations

        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.gamma = GAMMA
        self.batch_size = batch_size
        self.capacity = capacity

        self.buffer = replay_buffer(self.capacity)
        self.evaluate_net = Net(dem_states=self.d_states, num_actions=self.n_actions)  # the evaluate network
        self.target_net = Net(dem_states=self.d_states, num_actions=self.n_actions)  # the target network

        self.optimizer = torch.optim.Adam(
            self.evaluate_net.parameters(), lr=self.learning_rate)  # Adam is a method using to optimize the neural network

    def learn(self):
        if self.count % 100 == 0:
            self.target_net.load_state_dict(self.evaluate_net.state_dict())

        state, action, reward, tar_state, done = self.buffer.sample(self.batch_size)
        state = torch.as_tensor(state, dtype=torch.float32)
        reward = torch.as_tensor(reward, dtype=torch.float32)
        tar_state = torch.as_tensor(tar_state, dtype=torch.float32)
        
        cur_q = self.evaluate_net.forward(state)
        tar_q = self.evaluate_net.forward(tar_state)
        loss = torch.tensor(0.,dtype=torch.float32)

        for i in range(self.batch_size):
            cur = cur_q[i][action[i]]
            tar = reward[i] + self.gamma * (1 - done[i]) * torch.max(tar_q[i])
            loss += (cur - tar)**2 / self.batch_size

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        torch.save(self.target_net.state_dict(), self.DICT_PATH)

    def choose_action(self, state):
        with torch.no_grad():
            if random.random() < self.epsilon:
                return action_to_index(board=self.board, action=random.choice(self.board.get_Action()), color=self.color)
            
            state = torch.as_tensor(state, dtype=torch.float32)
            return torch.argmax(self.evaluate_net.forward(state)).item()

def train(color):
    board = chessboard()
    agent = Agent(board=board, color=color)
    oppo = minmax()
    episode = 100
    for _ in tqdm(range(episode)): #modified
        state = board_state_to_ndarray(board.state)
        while True:
            next_state = None
            if board.round % 2 == color:
                agent.count += 1

                action_idx = agent.choose_action(state)
                action = index_to_action(board=board, index=action_idx, color=color)
                next_state = board.get_NextState(action)
                done = board.isWin() or board.isLose()
                reward = eval_reward(board=board, action=action, state=next_state, color=color)
                next_state = board_state_to_ndarray(next_state)
                agent.buffer.insert(state, action_idx, reward, next_state=next_state, done=int(done))
                if agent.count >= 1000:
                    agent.learn()
            else:
                action = oppo.get_Action(state)
                next_state = board.get_NextState(action)
                next_state = board_state_to_ndarray(next_state)
            if done:
                break
            state = next_state
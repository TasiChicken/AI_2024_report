class minimax():
    '''
    state:
    state.state = [set(),set()] # [ black, white ]
    state.round 
    state.get_Action()
    state.get_NextState(action)
    state.isLose()
    state.isWin()
    '''
    
    def Next_state(self, state): 
        '''
        input : state
        output: next_state
        (state: chessboard)
        '''
        # 
        
        next_state = state
        return next_state
    
    def get_value(self, state, parameter):
        '''
        input : state, parameter
        output: value
        (state: chessboard)
        para = [num_black, num_white, eat, ate, black_line, white_line]
        '''
        
        return 1
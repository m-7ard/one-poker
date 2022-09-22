from random import randint, shuffle
from tkinter import *
import threading
import time


class Card():
    value_letters = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
    def __init__(self, suit, value):
        self.suit = suit
        self.letter = self.value_letters[value] if value in self.value_letters else None
        self.value = value
        self.ranking = 'High' if self.value > 7 else 'Low'
    
    def __repr__(self):
        if self.letter:
            return self.suit + self.letter
        else:
            return self.suit + str(self.value)


class Deck():
    def __init__(self, subdecks=3, split=2):
        self.cards = [Card(suit, value) for suit in ["♥","♠","♦","♣"] 
                  for value in range(2, 15) for _ in range(subdecks)]
        shuffle(self.cards)
        self.split = int(len(self.cards) / split)
        self.cards = self.cards[:self.split]
        self.expected_cards_left = {value: 4 * subdecks / split for value in range(2, 15)}


class Player():
    def __init__(self, ai):
        self.ai = ai
        self.hand = []
        self.balance = 10
        self.name = None
        self.high = 0
        self.low = 0
        self.position = None
        
    def draw(self, deck):
        while len(self.hand) != 2:
            card = deck.cards.pop()
            self.hand.append(card)

    def place_card(self, Button_Top, Button_Bottom):
        def return_card(position, button):
            nonlocal card
            card = self.hand[position]
            button['bg'] = 'OliveDrab4'
            button['disabledforeground'] = 'white'

        card = None
        if self.ai == True:
            if self.position == "Advantage" or self.position == "Disadvantage":
                card = sorted(self.hand, key=lambda card: card.value)[0]
            else:
                card = sorted(self.hand, key=lambda card: card.value)[1]
        else:
            Button_Top['command'] = lambda: return_card(0, Button_Top)
            Button_Bottom['command'] = lambda: return_card(1, Button_Bottom)
            while card == None:
                pass
        
        self.hand.remove(card)
        return card
        
    def bet(self, amount):
        self.balance -= amount
        return amount
    
    def __repr__(self):
        return self.name


class Gameboard():
    def __init__(self, *players):
        self.bets = {player: 0 for player in players}
        self.cards = {player: None for player in players}
        self.discard_pile = []
    
    def clear_board(self):
        self.bets = {player: 0 for player in self.bets}
        self.discard_pile.extend(self.cards.values())
        self.cards = {player: None for player in self.cards}


class Utility():
    """ Calculate the winning probability """
    def success_calc(available, reference):
        if reference > 7:
            population = sum([copies for (value, copies) in available.items() if value > 7])
            bigger_than = sum([copies for (value, copies) in available.items() if 7 < value < reference])
        elif reference <= 7:
            population = sum([copies for (value, copies) in available.items() if value <= 7])
            bigger_than = sum([copies for (value, copies) in available.items() if 7 >= value < reference])
        
        if reference == 14:
            return bigger_than / (population + available[2]) if (population + available[2]) else 0
        elif reference == 2:
            return available[14] / (population + available[14]) if (population + available[14]) else 0
        else:
            return bigger_than / population if population else 0
        
    
    """ Calculate martingale """
    def kelly_criterion(success_probability, odds=1):
        return success_probability - ((1 - success_probability) / odds)


class Game():
    def __init__(self, P1, P2, wager=1):
        # Define players
        self.P1 = Player(ai=P1)
        self.P1.name = 'P1'
        self.P2 = Player(ai=P2)
        self.P2.name = 'P2'

        # GUI
        self.GUI = GUI(self.P1, self.P2)
        self.thread1 = threading.Thread(target=self.GUI.run)
        self.thread1.start()

        # Randomize player order
        self.player_set = set((self.P1, self.P2))
        self.player_order = list(self.player_set)
        shuffle(self.player_order)

        # Initialize board; Define wage; Initialize deck
        self.Board = Gameboard(self.P1, self.P2)
        self.wager = wager
        self.Pile = Deck()
        
        # If the continue button should be pressed to go to the next round
        self.auto_continue = False

        # Global pick variable
        self.pick = None


        # Wait until all buttons have been created
        Flag.wait()
        self.assign_betting_commands()
    
    def assign_betting_commands(self):
        def return_pick(button_pick):
            self.pick = button_pick
        def continue_going():
            self.GUI.Button_Continue['state'] = 'disabled'
            Flag.set()

        self.GUI.Button_Check['command'] = lambda: return_pick('Check')
        self.GUI.Button_Raise['command'] = lambda: return_pick('Raise')
        self.GUI.Button_Fold['command'] = lambda: return_pick('Fold')
        self.GUI.Button_Call['command'] = lambda: return_pick('Call')
        self.GUI.Button_Continue['command'] = lambda: continue_going()

    """	Generate each player's high-low card count """
    def card_ranking(self):
        for player in self.player_set:
            player.high = len([card for card in player.hand if card.ranking == 'High'])
            player.low  = len([card for card in player.hand if card.ranking == 'Low'])

        for player in self.player_set:
            opponent = next(iter({player} ^ self.player_set))
            if player.high == 2 and opponent.high == 0:
                player.position = "Advantage"
            elif player.high == 0 and opponent.high >= 1:
                player.position = "Disadvantage"
            else:
                player.position = "Neutral"
                
        for player in self.player_set:
            self.GUI.attributes[player]['high']['text'] = player.high
            self.GUI.attributes[player]['low']['text'] = player.low

    """ Decide who goes first next round """
    def next_round_order(self):
        if self.Winner:
            self.player_order.remove(self.Winner)
            self.player_order.insert(0, self.Winner)

    """ Draw until 2 cards in hand """
    def draw_phase(self):
        for player in self.player_order:
            player.draw(self.Pile)

    """ Place a card from the hand into the Board's cards object """
    def decision_phase(self):
        for player in self.player_order:
            if player.ai == False:
                self.GUI.Button_Card_Top['text'] = player.hand[0]
                self.GUI.Button_Card_Top['state'] = 'normal'
                self.GUI.Button_Card_Bottom['text'] = player.hand[1]
                self.GUI.Button_Card_Bottom['state'] = 'normal'

            self.Board.cards[player] = player.place_card(self.GUI.Button_Card_Top, self.GUI.Button_Card_Bottom)
            self.GUI.attributes[player]['card']['text'] = 'Set Card'
            self.GUI.Button_Card_Top['state'] = 'disabled'
            self.GUI.Button_Card_Bottom['state'] = 'disabled'
    
    """ Regular Poker betting rules """
    def betting_phase(self):
        # Random AI pick.
        def ai_pick(player):
            # Define opponents; Calculate success probability; 
            opponent = next(iter(self.player_set ^ {player}))
            success_probability = Utility.success_calc(self.Pile.expected_cards_left, self.Board.cards[player].value)

            # Odds (preliminary) are defined as:
            if max(pot.values()) > player.balance + pot[player]:
                odds = pot[opponent] / (player.balance + pot[player])
            else:
                odds = 1

            # https://math.stackexchange.com/questions/1917807/game-theory-optimal-solution-to-2-player-betting-game
            random_factor = randint(0, 77) / 100

            # Max amount willing to bet
            max_bet = Utility.kelly_criterion(success_probability, odds) * (player.balance + pot[player])

            
            if player.balance == 0:
                # Player has all-inned
                self.pick = 'Check'

            elif player.balance <= pot[opponent] - pot[player]:
                # Player must all-in or fold
                if player.position == 'Advantage':
                    if pot[player] + player.balance <= max_bet and success_probability > random_factor:
                        self.pick = 'All in'
                    else:
                        self.pick = 'Fold'
                elif player.position == 'Disadvantage':
                    self.pick = 'Fold'
                elif player.position == 'Neutral':
                    if pot[player] + player.balance <= max_bet and success_probability > random_factor:
                        self.pick = 'All in'
                    else:
                        self.pick = 'Fold'

            elif pot[player] == pot[opponent]:
                # Player has same pot as the other player
                if player.position == 'Advantage':
                    if pot[player] + 1 <= max_bet and success_probability > random_factor:
                        self.pick = 'Raise'
                    else:
                        self.pick = 'Check'
                elif player.position == 'Disadvantage':
                    self.pick = 'Check'
                elif player.position == 'Neutral':
                    if pot[player] + 1 <= max_bet and success_probability > random_factor:
                        self.pick = 'Raise'
                    else:
                        self.pick = 'Check'
            
            elif pot[player] < pot[opponent]:
                # Player pot is less than the other player and is able to call it without all-inning
                if player.position == 'Advantage':
                    if max(pot.values()) + 1 <= max_bet and success_probability > random_factor:
                        self.pick = 'Raise'
                    else:
                        self.pick = 'Call'
                elif player.position == 'Disadvantage':
                    self.pick = 'Fold'
                elif player.position == 'Neutral':
                    if max(pot.values()) + 1 <= max_bet and success_probability > random_factor:
                        self.pick = 'Raise'
                    elif success_probability > random_factor:
                        self.pick = 'Call'
                    else:
                        self.pick = 'Fold'
        
        # Manual human pick
        def human_pick(player):
            opponent = next(iter(self.player_set ^ {player}))
            if player.balance == 0:
                self.GUI.Button_Check['state'] = 'normal'
            elif player.balance <= pot[opponent] - pot[player]:
                self.GUI.Button_Raise['text'] = 'All in'
                self.GUI.Button_Raise['state'] = 'normal'
                self.GUI.Button_Fold['state'] = 'normal'
            elif pot[player] == pot[opponent]:
                self.GUI.Button_Raise['state'] = 'normal'
                self.GUI.Entry_Raise['state'] = 'normal'
                self.GUI.Button_Check['state'] = 'normal'
                self.GUI.Button_Fold['state'] = 'normal'
            elif pot[player] < pot[opponent]:
                self.GUI.Button_Raise['state'] = 'normal'
                self.GUI.Entry_Raise['state'] = 'normal'
                self.GUI.Button_Call['state'] = 'normal'
                self.GUI.Button_Fold['state'] = 'normal'

            while self.pick == None:
                pass

            self.GUI.Button_Raise['state'] = 'disabled'
            self.GUI.Button_Raise['text'] = 'Raise'
            self.GUI.Entry_Raise['state'] = 'disabled'
            self.GUI.Button_Call['state'] = 'disabled'
            self.GUI.Button_Check['state'] = 'disabled'
            self.GUI.Button_Fold['state'] = 'disabled'
        

        # Define / reset winner
        self.Winner = None

        # Base wager
        pot = self.Board.bets
        for player in pot:
            pot[player] += player.bet(self.wager)
            self.GUI.attributes[player]['balance']['text'] = player.balance
            self.GUI.attributes[player]['pot']['text'] = pot[player]
        
        # Players in the current round. If you want to simulate players folding in a bigger game, etc.
        self.round_players = self.player_order.copy()

        # Initialize action list
        round_actions = ['start']

        # Start of the betting loop
        while (
               any([pot[player] != max(pot.values()) and player.balance for player in self.round_players])
               or 'start' in round_actions
            ):
            round_actions = []
            for player in self.round_players:
                while self.pick == None:
                    # Re/declare amount and pick, pick being a global variable
                    amount = 0

                    if player.ai:
                        ai_pick(player)
                    else:
                        human_pick(player)

                    self.pick = self.pick.lower()

                    if self.pick == 'check':
                        pass
                    elif self.pick == 'fold':
                        self.round_players.remove(player)
                    elif self.pick == 'call':
                        amount = max(pot.values()) - pot[player]
                        pot[player] += player.bet(amount)
                    elif self.pick == 'raise':
                        # Will only raise by the max bet + 1, can be changed to anything
                        amount = max(pot.values()) - pot[player] + 1 if player.ai \
                                 else self.GUI.Entry_Raise.get()
                        if str(amount).isdigit() == False or max(pot.values()) - pot[player] >= int(amount) or int(amount) > player.balance:
                            self.pick = None
                            continue
                        else:
                            amount = int(amount)
                            if amount == player.balance: 
                                self.pick = 'all in'
                            pot[player] += player.bet(amount)

                    elif self.pick == 'all in':
                        amount = player.bet(player.balance)
                        pot[player] += amount

                    round_actions.append(self.pick)
                    self.GUI.attributes[player]['balance']['text'] = player.balance
                    self.GUI.attributes[player]['pot']['text'] = pot[player]
                    self.GUI.Listbox_Log.insert(END, f'{player} {self.pick}s {amount if amount else str()}')

                # Reset pick
                self.pick = None
                self.GUI.attributes[player]['balance']['text'] = player.balance
                self.GUI.attributes[player]['pot']['text'] = pot[player]

                self.GUI.Listbox_Log.yview(END)
        
        # End of the betting loop

        # If there's only 1 player left, they will be declared winner.
        if len(self.round_players) == 1:
            self.Winner = next(iter(self.round_players))
            return
            
    # End of the betting phase

    """ All players reveal their cards; Winner is decided """
    def showdown_phase(self):
        # Reveal cards
        for player in self.player_set:
            self.GUI.attributes[player]['card']['text'] = self.Board.cards[player]


        # Check if there already is a winner, else determine winner / tie.
        if self.Winner:
            self.next_round_order()
            return
        
        for player in self.round_players:
            opponent = next(iter(set(self.round_players) ^ {player}))
            if self.Board.cards[player].value > self.Board.cards[opponent].value:
                if self.Board.cards[player].value == 14 and self.Board.cards[opponent].value == 2:
                    self.Winner = opponent
                    break
                else:
                    self.Winner = player
                    break

        self.next_round_order()

    """ Reallocate the bets to the winner, if there is one """
    def payout_phase(self):
        if self.Winner == None:
            for player in self.player_set:
                player.balance += self.Board.bets[player]
                self.GUI.attributes[player]['name']['bg'] = 'green yellow'

            self.GUI.Listbox_Log.insert(END, 'All players tie')
            self.GUI.Listbox_Log.itemconfig(END, {'bg': 'PaleGreen4', 'fg': 'black'})
        else:
            self.Winner.balance += sum(self.Board.bets.values())
            
            self.GUI.attributes[self.Winner]['name']['bg'] = 'green'
            self.GUI.Listbox_Log.insert(END, f'{self.Winner.name} wins')
            self.GUI.Listbox_Log.itemconfig(END, {'bg': 'PaleGreen4', 'fg': 'black'})
        
        for player in self.player_set:
            self.GUI.attributes[player]['balance']['text'] = player.balance
            self.GUI.attributes[player]['pot']['text'] = 0

        self.GUI.Listbox_Log.yview(END)
    
    """ Eliminate any player with a balance of 0 """
    def player_elimination(self):
        for player in self.player_order:
            if player.balance == 0:
                self.player_order.remove(player)
                self.player_set.remove(player)
                self.Board.cards.pop(player)
                self.Board.bets.pop(player)
                self.GUI.attributes[player]['bg'] = 'red'
    
    """ Rest away the cards on the board from the (expected) amount that left """
    def adjust_cards_left(self):
        for card in self.Board.cards.values():
            if self.Pile.expected_cards_left[card.value]:
                self.Pile.expected_cards_left[card.value] -= 1
    
    """ Update GUI round label """
    def update_round(self):
        self.round += 1
        self.GUI.Label_Round['text'] = f'Round {self.round}'

        self.GUI.Listbox_Log.insert(END, f'Cards left: {len(self.Pile.cards)}')
        self.GUI.Listbox_Log.itemconfig(END, {'bg': 'PaleGreen3', 'fg': 'black'})

        self.GUI.Listbox_Log.insert(END, f'Round {self.round}')
        self.GUI.Listbox_Log.itemconfig(END, {'bg': 'PaleGreen3', 'fg': 'black'})
        

        self.GUI.Listbox_Log.yview(END)

    def go_to_next_round(self):
        if self.auto_continue == False:
            self.GUI.Button_Continue['state'] = 'normal'
            Flag.clear()
        
        Flag.wait()
        if self.GUI.Button_Card_Top['bg'] == 'OliveDrab4':
            self.GUI.Button_Card_Top['text'] = ''
        elif self.GUI.Button_Card_Bottom['bg'] == 'OliveDrab4':
            self.GUI.Button_Card_Bottom['text'] = ''
        self.GUI.Apply_Theme(self.GUI.Label_Name_Player_1, self.GUI.Indicator_Theme)
        self.GUI.Apply_Theme(self.GUI.Label_Name_Player_2, self.GUI.Indicator_Theme)
        self.GUI.Apply_Theme(self.GUI.Button_Card_Top, self.GUI.Button_Theme)
        self.GUI.Apply_Theme(self.GUI.Button_Card_Bottom, self.GUI.Button_Theme)
        self.GUI.attributes[self.P1]['card']['text'] = ''
        self.GUI.attributes[self.P2]['card']['text'] = ''
        


    """ Main loop """
    def run(self):
        self.round = 0
        Flag.wait()
        self.assign_betting_commands()
        while len(self.player_order) > 1:
            time.sleep(1)
            self.update_round()
            self.draw_phase()
            self.card_ranking()
            self.decision_phase()
            self.betting_phase()
            self.showdown_phase()
            self.payout_phase()
            self.player_elimination()
            self.adjust_cards_left()
            self.Board.clear_board()
            if len(self.Pile.cards) == 0:
                self.GUI.Listbox_Log.insert(END, 'No cards to draw')
                self.GUI.Listbox_Log.itemconfig(END, {'bg': 'black', 'fg': 'yellow green'})
                self.GUI.Listbox_Log.insert(END, 'Game results in tie')
                self.GUI.Listbox_Log.itemconfig(END, {'bg': 'black', 'fg': 'yellow green'})
                return
                
            self.go_to_next_round()
        
        print(f'{self.player_order[0]} is the game winner.')

class GUI():
    def __init__(self, P1, P2):
        self.P1 = P1
        self.P2 = P2
        self.label_width = 8
        self.label_height = 1
        self.Indicator_Theme = {
            'width': self.label_width, 
            'height': self.label_height, 
            'relief': RAISED,
            'bg': 'SpringGreen4',
            'fg': 'white',
        }
        self.Score_Theme = {
            'width': self.label_width, 
            'height': self.label_height, 
            'relief': GROOVE,
            'bg': 'DarkSeaGreen1',
            'fg': 'Black',
        }
        self.Button_Theme = {
            'relief': RAISED, 
            'state': 'disabled',
            'bg': 'Tan4', 
            'fg': 'white',
            'activebackground': 'Tan4', 
            'activeforeground': 'white',
        }
        self.Entry_Theme = {
            'width': self.label_width, 
            'relief': SUNKEN, 
            'state': 'disabled', 
            'bg': 'PaleGreen1',
            'disabledbackground': 'PaleGreen3',
        }
    
    def Apply_Theme(self, Tkinter_Object, Theme):
        for option, value in Theme.items():
            Tkinter_Object[option] = value

    def classify(self, P1, P2):
        self.attributes = {
            P1: {
                'name': self.Label_Name_Player_1,
                'balance': self.Label_Balance_Player_1,
                'high': self.Label_High_Player_1,
                'low': self.Label_Low_Player_1,
                'card': self.Label_Card_Player_1,
                'pot': self.Label_Pot_Player_1
            },
            P2: {
                'name': self.Label_Name_Player_2,
                'balance': self.Label_Balance_Player_2,
                'high': self.Label_High_Player_2,
                'low': self.Label_Low_Player_2,
                'card': self.Label_Card_Player_2,
                'pot': self.Label_Pot_Player_2
            }
        }


        self.Label_Name_Player_1['text'] = f"{P1.name} {'(AI)' if P1.ai else ''}"
        self.Label_Balance_Player_1['text'] = P1.balance
        self.Label_High_Player_1['text'] = 0
        self.Label_Low_Player_1['text'] = 0
        self.Label_Card_Player_1['text'] = ''
        self.Label_Pot_Player_1['text'] = 0


        self.Label_Name_Player_2['text'] = f"{P2.name} {'(AI)' if P2.ai else ''}"
        self.Label_Balance_Player_2['text'] = P2.balance
        self.Label_High_Player_2['text'] = 0
        self.Label_Low_Player_2['text'] = 0
        self.Label_Card_Player_2['text'] = ''
        self.Label_Pot_Player_2['text'] = 0

    def run(self):
        self.Master = Tk()
        self.Master.resizable(False, False)
        
        self.Frame_Indicators = Frame(self.Master)
        self.Frame_Player_1 = Frame(self.Master)
        self.Frame_Player_2 = Frame(self.Master)
        self.Frame_Betting = Frame(self.Master)

        self.Frame_Indicators.pack(side='top', fill='x')
        self.Frame_Player_1.pack(side='top',fill='x')
        self.Frame_Player_2.pack(side='top', fill='x')

        """ Indicator Labels """
        self.Label_Round =      Label(self.Frame_Indicators, text='Round 0')
        self.Label_Balance =    Label(self.Frame_Indicators, text='Balance')
        self.Label_High =       Label(self.Frame_Indicators, text='High')
        self.Label_Low =        Label(self.Frame_Indicators, text='Low')
        self.Label_Pot =        Label(self.Frame_Indicators, text='Pot')
        self.Label_Card =       Label(self.Frame_Indicators, text='Card')

        self.Apply_Theme(self.Label_Round, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Balance, self.Indicator_Theme)
        self.Apply_Theme(self.Label_High, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Low, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Pot, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Card, self.Indicator_Theme)

        self.Label_Round.pack(side='left',)
        self.Label_Balance.pack(side='left',)
        self.Label_High.pack(side='left',)
        self.Label_Low.pack(side='left',)
        self.Label_Pot.pack(side='left',)
        self.Label_Card.pack(side='left',)

        """ Player 1 Labels"""
        self.Label_Name_Player_1 =      Label(self.Frame_Player_1, text='Player 1')
        self.Label_Balance_Player_1 =   Label(self.Frame_Player_1, text='0')
        self.Label_High_Player_1 =      Label(self.Frame_Player_1, text='0')
        self.Label_Low_Player_1 =       Label(self.Frame_Player_1, text='0')
        self.Label_Pot_Player_1 =       Label(self.Frame_Player_1, text='0')
        self.Label_Card_Player_1 =      Label(self.Frame_Player_1, text='None')

        self.Apply_Theme(self.Label_Name_Player_1, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Balance_Player_1, self.Score_Theme)
        self.Apply_Theme(self.Label_High_Player_1, self.Score_Theme)
        self.Apply_Theme(self.Label_Low_Player_1, self.Score_Theme)
        self.Apply_Theme(self.Label_Pot_Player_1, self.Score_Theme)
        self.Apply_Theme(self.Label_Card_Player_1, self.Score_Theme)

        self.Label_Name_Player_1.pack(side='left',)
        self.Label_Balance_Player_1.pack(side='left',)
        self.Label_High_Player_1.pack(side='left',)
        self.Label_Low_Player_1.pack(side='left',)
        self.Label_Pot_Player_1.pack(side='left',)
        self.Label_Card_Player_1.pack(side='left',)

        """ Player 2 Labels """
        self.Label_Name_Player_2 =      Label(self.Frame_Player_2, text='Player 2')
        self.Label_Balance_Player_2 =   Label(self.Frame_Player_2, text='0')
        self.Label_High_Player_2 =      Label(self.Frame_Player_2, text='0')
        self.Label_Low_Player_2 =       Label(self.Frame_Player_2, text='0')
        self.Label_Pot_Player_2 =       Label(self.Frame_Player_2, text='0')
        self.Label_Card_Player_2 =      Label(self.Frame_Player_2, text='None')

        self.Apply_Theme(self.Label_Name_Player_2, self.Indicator_Theme)
        self.Apply_Theme(self.Label_Balance_Player_2, self.Score_Theme)
        self.Apply_Theme(self.Label_High_Player_2, self.Score_Theme)
        self.Apply_Theme(self.Label_Low_Player_2, self.Score_Theme)
        self.Apply_Theme(self.Label_Pot_Player_2, self.Score_Theme)
        self.Apply_Theme(self.Label_Card_Player_2, self.Score_Theme)

        self.Label_Name_Player_2.pack(side='left',)
        self.Label_Balance_Player_2.pack(side='left',)
        self.Label_High_Player_2.pack(side='left',)
        self.Label_Low_Player_2.pack(side='left',)
        self.Label_Pot_Player_2.pack(side='left',)
        self.Label_Card_Player_2.pack(side='left',)

        """ Betting Window """
        self.Frame_Betting =            Frame(self.Master)
        self.Frame_Betting_Left =       Frame(self.Frame_Betting)
        self.Frame_Betting_Right =      Frame(self.Frame_Betting)
        self.Frame_Betting_Top =        Frame(self.Frame_Betting_Left)
        self.Frame_Betting_Bottom =     Frame(self.Frame_Betting_Left)

        for x in range(4):
            Label(self.Frame_Betting_Top, width=self.label_width, relief=RAISED).grid(row=0, column=x)
        for x in range(4):
            Label(self.Frame_Betting_Bottom, width=self.label_width, relief=RAISED).grid(row=0, column=x)

        # Top
        self.Button_Card_Top =  Button(self.Frame_Betting_Top)
        self.Button_Raise =     Button(self.Frame_Betting_Top, text='Raise')
        self.Button_Call =      Button(self.Frame_Betting_Top, text='Call')
        self.Button_Check =     Button(self.Frame_Betting_Top, text='Check')

        self.Apply_Theme(self.Button_Card_Top, self.Button_Theme)
        self.Apply_Theme(self.Button_Raise, self.Button_Theme)
        self.Apply_Theme(self.Button_Call, self.Button_Theme)
        self.Apply_Theme(self.Button_Check, self.Button_Theme)

        # Bottom
        self.Button_Card_Bottom = Button(self.Frame_Betting_Bottom)
        self.Entry_Raise = Entry(self.Frame_Betting_Bottom)
        self.Button_Fold = Button(self.Frame_Betting_Bottom, text='Fold')
        self.Button_Continue = Button(self.Frame_Betting_Bottom, text='Continue')

        self.Apply_Theme(self.Button_Card_Bottom, self.Button_Theme)
        self.Apply_Theme(self.Entry_Raise, self.Entry_Theme)
        self.Apply_Theme(self.Button_Fold, self.Button_Theme)
        self.Apply_Theme(self.Button_Continue, self.Button_Theme)

        # Top Packing
        self.Button_Card_Top.grid(row=0, column=0, sticky='ew')
        self.Button_Raise.grid(row=0, column=1, sticky='ew')
        self.Button_Call.grid(row=0, column=2, sticky='ew')
        self.Button_Check.grid(row=0, column=3, sticky='ew')

        # Bottom Packing
        self.Button_Card_Bottom.grid(row=0, column=0, sticky='ew')
        self.Entry_Raise.grid(row=0, column=1, columnspan=1,sticky='ewns')
        self.Button_Fold.grid(row=0, column=2, sticky='ew')
        self.Button_Continue.grid(row=0, column=3, sticky='ew')

        # Frame Packing
        self.Frame_Betting.pack(side='top', anchor='w')
        self.Frame_Betting_Left.pack(side='left')
        self.Frame_Betting_Right.pack(side='right')
        self.Frame_Betting_Top.pack(side='top', anchor='w')
        self.Frame_Betting_Bottom.pack(side='top', anchor='w')

        """ Action Log """
        self.Frame_Log = Frame(self.Frame_Betting_Right)
        self.Frame_Log.pack(side='left')
        
        self.Listbox_Log = Listbox(
            self.Frame_Log, 
            relief=SUNKEN, 
            height=3, 
            bg='PaleGreen1', 
            selectbackground='Tan1', 
            selectforeground='black')
        self.Listbox_Log.pack()

        """ Fill in the values using the Game instance information """
        self.classify(self.P1, self.P2)

        Flag.set()
        self.Master.mainloop()






Flag = threading.Event()
Game_1 = Game(False, True)



Game_1.run()



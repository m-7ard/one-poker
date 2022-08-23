from random import randint, shuffle


class Card():
    value_letters = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
    def __init__(self, suit, value):
        self.suit = suit
        self.letter = self.value_letters[value] if value in self.value_letters else None
        self.value = value
        self.ranking = 'High' if self.value > 7 else 'Low'
        self.face_up = False
    
    def flip(self):
        if self.face_up == False:
            self.face_up = True
        else:
            self.face_up = False
    
    def __repr__(self):
        if self.face_up:
            if self.letter:
                return self.suit + self.letter
            else:
                return self.suit + str(self.value)
        else:
            return "Face-Down Card"


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
            card.flip()
            self.hand.append(card)

    def place_card(self):
        if self.ai == True:
            if self.position == "Advantage" or self.position == "Disadvantage":
                card = sorted(self.hand, key=lambda card: card.value)[0]
            else:
                card = sorted(self.hand, key=lambda card: card.value)[1]
            self.hand.remove(card)
            card.flip()
            return card
        else:
            while True:
                message = f'\nSelect card to place down:\n0) {self.hand[0]}\n1) {self.hand[1]}\n'
                card_position = int(input(message))
                if card_position > 1:
                    print('Can only choose 0 or 1.')
                else:
                    card = self.hand.pop(card_position)
                    card.flip()
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
            bigger_than = sum([copies for (value, copies) in available.items() if value < reference and value > 7])
        elif reference <= 7:
            population = sum([copies for (value, copies) in available.items() if value <= 7])
            bigger_than = sum([copies for (value, copies) in available.items() if value < reference and value <= 7])
        
        return bigger_than / population if population else 0
    
    """ Calculate martingale """
    def kelly_criterion(success_probability, odds=1):
        return success_probability - ((1 - success_probability) / odds)


class Game():
    def __init__(self, wager=1):
        # Define players
        self.Human = Player(True)
        self.Human.name = 'Human'
        self.AI = Player(True)
        self.AI.name = 'AI'

        # Randomize player order
        self.player_set = set((self.Human, self.AI))
        self.player_order = list(self.player_set)
        shuffle(self.player_order)

        # Initialize board; Define wage; Initialize deck
        self.Board = Gameboard(*list(self.player_set))
        self.wager = wager
        self.Pile = Deck()

    """	Generate each player's high-low card count """
    def card_ranking(self):
        for some_player in self.player_set:
            some_player.high = len([card for card in some_player.hand if card.ranking == 'High'])
            some_player.low  = len([card for card in some_player.hand if card.ranking == 'Low'])
            print(f'{some_player.name} => High: {some_player.high} Low: {some_player.low}')
        print('-----------------------')

        for some_player in self.player_set:
            opponents = {some_player} ^ self.player_set
            if some_player.high == 2 and all(opponent.high == 0 for opponent in opponents):
                some_player.position = "Advantage"
            elif some_player.high == 0 and all(opponent.high >= 1 for opponent in opponents):
                some_player.position = "Disadvantage"
            else:
                some_player.position = "Neutral"
        
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
            self.Board.cards[player] = player.place_card()
    
    """ Regular Poker betting rules """
    def betting_phase(self):
        # Random AI pick.
        def ai_pick(player):
            # Define opponents; Calculate success probability; 
            opponents = self.player_set ^ {player}
            success_probability = Utility.success_calc(self.Pile.expected_cards_left, self.Board.cards[player].value)

            # Odds (preliminary) are defined as:
            if max(pot.values()) > player.balance + pot[player]:
                odds = sum([pot[opponent] for opponent in opponents]) / (player.balance + pot[player])
            else:
                odds = sum([pot[opponent] for opponent in opponents]) / max(pot.values())

            # https://math.stackexchange.com/questions/1917807/game-theory-optimal-solution-to-2-player-betting-game
            random_factor = randint(0, 77) / 100

            # Max amount willing to bet
            max_bet = Utility.kelly_criterion(success_probability, odds) * (player.balance + pot[player])

            
            if player.balance == 0:
                # Player has all-inned
                return 'Check'

            elif any(player.balance <= pot[opponent] - pot[player] for opponent in opponents):
                # Player must all-in or fold
                if player.position == 'Advantage':
                    if pot[player] + player.balance <= max_bet and success_probability > random_factor:
                        return 'All in'
                    else:
                        return 'Fold'
                elif player.position == 'Disadvantage':
                    return 'Fold'
                elif player.position == 'Neutral':
                    if pot[player] + player.balance <= max_bet and success_probability > random_factor:
                        return 'All in'
                    else:
                        return 'Fold'

            elif all(pot[player] >= pot[opponent] for opponent in opponents):
                # Player has same pot as other players; or bigger in case of a +2 player game 
                if player.position == 'Advantage':
                    if pot[player] + 1 <= max_bet and success_probability > random_factor:
                        return 'Raise'
                    else:
                        return 'Check'
                elif player.position == 'Disadvantage':
                    return 'Check'
                elif player.position == 'Neutral':
                    if pot[player] + 1 <= max_bet and success_probability > random_factor:
                        return 'Raise'
                    else:
                        return 'Check'
            
            elif any(pot[player] < pot[opponent] for opponent in opponents):
                # Player pot is less than some other player and is able to call it without all-inning
                if player.position == 'Advantage':
                    if max(pot.values()) + 1 <= max_bet and success_probability > random_factor:
                        return 'Raise'
                    else:
                        return 'Call'
                elif player.position == 'Disadvantage':
                    return 'Fold'
                elif player.position == 'Neutral':
                    if max(pot.values()) + 1 <= max_bet and success_probability > random_factor:
                        return 'Raise'
                    elif success_probability > random_factor:
                        return 'Call'
                    else:
                        return 'Fold'
        
        # Manual human pick
        def human_pick(player):
            opponents = self.player_set ^ {player}
            if player.balance == 0:
                return input("['Check']")
            elif any(player.balance <= pot[opponent] - pot[player] for opponent in opponents):
                return input("['All in', 'Fold']")
            elif all(pot[player] >= pot[opponent] for opponent in opponents):
                return input("['Raise', 'Check', 'Fold']")
            elif any(pot[player] < pot[opponent] for opponent in opponents):
                return input("['Call', 'Raise', 'Fold']")
            else:
                return input("['Check']")
        
        # Console log picks
        def print_pick(pick, Some_Player, amount=0):
                if amount:
                    print(f'{Some_Player.name} {pick}s {amount}')
                else:
                    print(f'{Some_Player.name} {pick}s')

        # Define / reset winner
        self.Winner = None

        # Base wager
        pot = self.Board.bets
        for player in pot:
            pot[player] += player.bet(self.wager)
        
        # Players in the current round. If you want to simulate players folding in a bigger game, etc.
        round_players = self.player_order.copy()

        # Initialize action list
        round_actions = ['start']

        # Start of the betting loop
        while (
               any([pot[player] != max(pot.values()) and player.balance for player in round_players])
               or 'start' in round_actions
            ):

            # Console log pot; Empty the round actions; Check if there's only 1 player left.
            pot_information = 'Pot >> '
            for player in self.player_set:
                pot_information += f'{player.name}: {pot[player]} | '
            print(pot_information)

            round_actions = []

            # If there's only 1 player left, they will be declared winner.
            if len(round_players) == 1:
                self.Winner = next(iter(round_players))
                return

            for player in round_players:
                amount = 0
                pick = ai_pick(player) if player.ai else human_pick(player)
                pick = pick.lower()
                if pick == 'check':
                    pass
                elif pick == 'fold':
                    round_players.remove(player)
                elif pick == 'call':
                    amount = max(pot.values()) - pot[player]
                    pot[player] += player.bet(amount)
                elif pick == 'raise':
                    while True:
                        # Will only raise by the max bet + 1, can be changed to anything
                        amount = max(pot.values()) - pot[player] + 1 if player.ai \
                                 else int(input('Bet amount: '))
                        if amount <= player.balance and amount > 0:
                            if amount == player.balance: 
                                pick = 'all in'
                            pot[player] += player.bet(amount)
                            break
                elif pick == 'all in':
                    amount = player.bet(player.balance)
                    pot[player] += amount

                round_actions.append(pick)
                print_pick(pick, player, amount)
        
        # End of the betting loop

    # End of the betting phase

    """ All players reveal their cards; Winner is decided """
    def showdown_phase(self):
        # Reveal cards; Print the winner, if there is one, else print tie
        def print_winner():
            for player in self.Board.cards:
                print(f'『{player.name}: {self.Board.cards[player]}』')

            if self.Winner == None:
                print('All players tie.')
            else:
                print(f'{self.Winner.name} wins')
        
        board_cards = self.Board.cards
        board_values = [card.value for card in board_cards.values()]

        for player in board_cards:
            board_cards[player].flip()
        
        if self.Winner:
            print_winner()
            self.next_round_order()
            return
        
        for player in board_cards:
            opponents = self.player_set ^ {player}
            if all(board_cards[player].value > board_cards[opponent].value for opponent in opponents):
                if all(two_ace in board_values for two_ace in [2, 14]):
                    if board_values.count(2) == 1:
                        self.Winner = list(board_cards.keys())[board_values.index(2)]
                        break
                else:
                    self.Winner = player
                    break

        print_winner()
        self.next_round_order()

    """ Reallocate the bets to the winner, if there is one """
    def payout_phase(self):
        if self.Winner == None:
            for player in self.player_set:
                player.balance += self.Board.bets[player]
        else:
            self.Winner.balance += sum(self.Board.bets.values())
    
    """ Eliminate any player/s with a balance of 0 """
    def player_elimination(self):
        for player in self.player_order:
            if player.balance == 0:
                self.player_order.remove(player)
                self.player_set.remove(player)
                self.Board.cards.pop(player)
                self.Board.bets.pop(player)
    
    """ Rest away the cards on the board from the (expected) amount that left """
    def adjust_cards_left(self):
        for card in self.Board.cards.values():
            if self.Pile.expected_cards_left[card.value]:
                self.Pile.expected_cards_left[card.value] -= 1

    """ Main loop """
    def run(self):
        round = 0
        while len(self.player_order) > 1:
            round += 1
            print(f'\n〚Round {round} start〛\nCards discarded: {self.Board.discard_pile}')
            for player in sorted(self.player_order, key=lambda player: player.name):
                print(f'{player.name} balance: {player.balance}')
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
                print('Players ran out of cards to draw. Game results in a draw.')
                return

Game().run()
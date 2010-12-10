import itertools

class Rotator:
    def __init__(self, players):
        # First player to act should always be first in this list
        self.players = players
        self.lastBettor = None
        self.lastBet = 0
        self.lastRaise = 0
        self.capBettor = None
        # This is both regular bets and all-in capped bets
        self.currentBet = 0

    def setBetSize(self, bet):
        self.lastBet = bet
        self.lastRaise = bet
    def setRaise(self, rai):
        self.lastRaise = rai

    def finishBetting(self, player):
        if self.lastBettor == player:
            # No one decided to raise the raiser
            self.bettingClosed = True
            if (self.capBettor is not None and
                not self.reOpenBetting):
                # But a shorty did go all-in, so we re-open
                # betting temporarily.
                self.reOpenBetting = True
            else:
                self.bettingFinished = True
                return True
        return False

    def run(self):
        self.bettingFinished = False
        # Whether to re-open betting when a shorty goes all-in
        # and caps the betting
        self.reOpenBetting = False
        # Betting Round is closed.
        self.bettingClosed = False

        # We always need at least 2 players at the table
        assert(len(self.players) > 1)

        while not self.bettingFinished:
            for player in self.players:
                # Skip over players that have folded.
                if not player.stillActive:
                    continue
                # And players that are all-in
                if player.isAllIn:
                    # If betting was re-opened by a shorty going
                    # all-in, then everyone had a chance to call
                    # so finished up.
                    if self.bettingClosed and self.reOpenBetting:
                        self.bettingFinished = True
                        break
                    # Or player went all-in and no-one else re-raised
                    elif self.finishBetting(player):
                        break
                    # Skip all-in players since they can't act
                    continue

                # Set to first available player UTG
                # This indicates when the table has done a full circle
                if self.lastBettor is None:
                    self.lastBettor = player
                elif self.finishBetting(player):
                    break

                # Special action for when the round was completed
                # And no-one raised the raiser but shorty went all-in
                # for less then the last raise.
                if self.bettingClosed and self.reOpenBetting:
                    # Players can only call or fold.
                    self.currentBet = self.capBettor.betPlaced
                    yield player, True
                    # Must match current bet.
                    if (not player.isAllIn and
                        player.betPlaced != self.currentBet):
                        # Fold
                        player.stillActive = False
                    continue

                # Current price to call
                self.currentBet = self.lastBet
                # Unless someone went all-in for less than a raise
                if self.capBettor is not None:
                    assert(self.capBettor.betPlaced > self.lastBet)
                    self.currentBet = self.capBettor.betPlaced

                # False = betting is not capped, player can raise
                cap = False
                # Check still some playing players left
                if self.oneBettingPlayer():
                    cap = True

                yield player, cap

                if (player.betPlaced < self.lastBet or
                    not player.stillActive):
                    self.deactivatePlayer(player)
                    # If only 1 player remains cos everyone folded
                    # then finish up.
                    if self.onePlayer():
                        self.bettingFinished = True
                        break
                elif player.betPlaced == self.currentBet:
                    # Call
                    pass
                elif player.betPlaced > self.lastBet:
                    # Anything but a normal minraise is considered
                    # an allin by the player.
                    if player.betPlaced < self.minRaise():
                        # Player went all-in for less than a raise
                        # Caps betting
                        if (self.capBettor is None or
                            self.currentBet < player.betPlaced):
                            self.capBettor = player
                            player.isAllIn = True
                    else:
                        # Normal raise situation.
                        self.capBettor = None

                        # Re-opened betting so new price to call.
                        self.lastRaise = player.betPlaced - self.lastBet
                        self.lastBet = player.betPlaced
                        self.lastBettor = player
                else:
                    # Something's wrong!
                    assert(False)
    
    def deactivatePlayer(self, player):
        # exception case
        if not player.isAllIn:
            # Fold
            player.stillActive = False
            if self.lastBettor == player:
                self.lastBettor = None

    def onePlayer(self):
        numActivePlayers = \
            len([p for p in self.players if p.stillActive])
        assert(numActivePlayers > 0)
        return numActivePlayers < 2
    def oneBettingPlayer(self):
        numActiveNonAllInPlayers = \
            len([p for p in self.players if p.stillActive and not p.isAllIn])
        return numActiveNonAllInPlayers < 2

    def minRaise(self):
        if self.capBettor is not None:
            return self.lastBet + 2*self.lastRaise
        return self.lastBet + self.lastRaise
    def call(self):
        return self.currentBet

    class SidePot:
        def __init__(self, size):
            self.betSize = size
            self.potSize = 0
            self.contestors = []
        def notation(self):
            players = [p.parent.nickname for p in self.contestors]
            return {'betsize': self.betSize, 'potsize': self.potSize,
                    'players': players}
        def __repr__(self):
            return '%d %d %s'%(self.betSize, self.potSize, self.contestors)

    def createPots(self):
        self.players.sort(key=lambda p: p.betPlaced)
        sidePots = []
        excessCash = 0
        for player in self.players:
            player.betPlaced += player.darkBet
            for sidePot in sidePots:
                player.betPlaced -= sidePot.betSize
                sidePot.potSize += sidePot.betSize
                if player.stillActive:
                    sidePot.contestors.append(player)

            if not player.stillActive:
                excessCash += player.betPlaced
                continue
            else:
                # new side pot!
                if player.betPlaced > 0:
                    sidePot = self.SidePot(player.betPlaced)
                    player.betPlaced -= sidePot.betSize
                    sidePot.potSize = sidePot.betSize + excessCash
                    excessCash = 0
                    sidePot.contestors.append(player)
                    sidePots.append(sidePot)
        return sidePots

if __name__ == '__main__':
    class P:
        def __init__(self, s):
            self.nickname = s
    seats = [P('UTG'), P('UTG+1'), P('UTG+2'), P('MP'), P('HJ'), P('CO'),
             P('BTN'), P('SB'), P('BB')]
    #seats = [P('a'), P('b'), P('c')]
    r = Rotator(seats)
    bb = 2
    r.setSeatBetPlaced(-2, bb/2)
    r.setSeatBetPlaced(-1, 1)
    r.setBetSize(bb)
    for player, capped in r.run():
        print '---------'
        print '%s bet %d to %d'%(r.lastBettor, r.lastRaise, r.lastBet)
        print r.capBettor, r.currentBet, capped
        if not capped:
            print 'call=%d, minraise=%d'%(r.call(), r.minRaise())
        else:
            print 'call=%d'%r.currentBet
        print
        print '%s (%d)'%(player, player.betPlaced)
        cc = raw_input()
        if cc[0] == 'a':
            s = int(cc[1:])
            player.isAllIn = True
        else:
            s = int(cc)
        player.betPlaced = s
    pots = r.createPots()
    for p in pots:
        print p.betSize, p.potSize, p.contestors


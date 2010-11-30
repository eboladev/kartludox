import script, table
from twisted.internet import reactor

class Schedule:
    def __init__(self):
        self.started = False
    def callback(self, functor, secs):
        # If already scheduled then make sure not to schedule event twice.
        if not self.started:
            print('A new game will begin in %d seconds.'%secs)
        started = True
        reactor.callLater(secs, functor)
    def clear(self):
        print('Cancelled callback.')

class Handler:
    """When the game starts then the table notifies this handler."""
    def __init__(self, adapter):
        self.running = False
        self.adapter = adapter
        self.script = None
        self.actIter = None
        self.currentAct = None
    def start(self, script):
        self.running = True
        self.script = script
        self.actIter = script.run()

        self.currentAct = self.actIter.next()
        self.displayAct()
    def displayAct(self):
        for line in self.currentAct.__repr__().split('\n'):
            self.adapter.reply(line)
    def update(self, player, response):
        if not self.running:
            return
        if player != self.currentAct.player.nickname:
            self.adapter.reply('Don\'t act out of turn!')
            return
        if response[0] not in self.currentAct.actionNames():
            self.displayAct()
            return
        try:
            self.currentAct = self.actIter.send(response)
            # handle cards dealt .etc here
            if isinstance(self.currentAct, script.CardsDealt):
                self.displayAct()
                self.currentAct = self.actIter.next()
            self.displayAct()
        except StopIteration:
            self.adapter.reply('END!!')
            self.start(self.script)
    def stop(self):
        self.running = False
        # award pot to remaining player sitting in.
        print 'stopped'

class Adapter:
    def __init__(self, prot, chan):
        reload(script)
        reload(table)
        self.prot = prot
        self.chan = chan
        self.cash = table.Table(9, 0.25, 0.5, 0, 5000, 25000)
        self.cash.registerScheduler(Schedule())
        self.handler = Handler(self)
        self.cash.registerHandler(self.handler)
        self.cash.setStartupDelayTime(1)

        ###
        self.cash.addPlayer('a', 0)
        self.cash.addPlayer('b', 1)
        self.cash.addPlayer('c', 2)
        self.cash.addPlayer('d', 3)
        self.cash.addMoney('a', 5000)
        self.cash.addMoney('b', 7000)
        self.cash.addMoney('c', 6000)
        self.cash.addMoney('d', 8000)
        self.cash.sitIn('a')
        self.cash.sitIn('b')
        self.cash.sitIn('c')
        self.cash.sitIn('d')
    def msg(self, user, message):
        print('%s: %s'%(user, message))
        message = message.split(' ')
        command = message[0]
        player = message[1]
        params = message[2:]
        if command == 'reg':
            self.cash.addPlayer(player, int(params))
        elif command == 'buyin':
            self.cash.addMoney(player, int(params))
        elif command == 'sitin':
            self.cash.sitIn(player)
        elif command == 'sitout':
            self.cash.sitOut(player)
            self.handler.update(player, (script.Action.SitOut,))
        elif command == 'postsb':
            self.handler.update(player, (script.Action.PostSB,))
        elif command == 'postbb':
            self.handler.update(player, (script.Action.PostBB,))
        elif command == 'postsbbb':
            self.handler.update(player, (script.Action.PostSBBB,))
        elif command == 'call':
            self.handler.update(player, (script.Action.Call,))
        elif command == 'fold':
            self.handler.update(player, (script.Action.Fold,))
        elif command == 'raise':
            self.handler.update(player, (script.Action.Raise, \
                int(params)))
        elif command == 'show':
            for line in self.cash.__repr__().split('\n'):
                self.reply(line)
            self.reply('Pots: %s'%self.handler.script.pots)
        print self.cash
    def reply(self, message):
        self.prot.msg(self.chan, message)
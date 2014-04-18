#! python

import democlient
import sensationprotocol_pb2 as sensationprotocol

client = democlient.DemoClient()
client.connect('localhost', 10000)

client.send('whatever this is')
client.send('something else')

command = sensationprotocol.Command()
command.name = 'wat'
command.id = 12


client.send(command.SerializeToString())

client.disconnect()
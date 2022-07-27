import libtcodpy as libtcod
import math
import textwrap

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20
MAP_HEIGHT = 43
MAP_WIDTH = 80
MAX_ROOM_SIZE = 10
MIN_ROOM_SIZE = 6
MAX_ROOMS = 30
color_dark_wall = libtcod.Color(0,0,100)
color_dark_ground = libtcod.Color(50,50,150)
color_light_wall = libtcod.Color(130,110,50)
color_light_ground = libtcod.Color(200,180,50)
FOV_ALGO = 10
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10
BAR_WIDTH = 20
panelheight = 7
panely = SCREEN_HEIGHT - panelheight
MAX_ROOM_MONSTERS = 3
MAXROOMITEMS = 2
gamestate = 'playing'
player_action = None
msgx = BAR_WIDTH+2
msgwidth = SCREEN_WIDTH - BAR_WIDTH - 2
msgheight = panelheight-1
inventorywidth = 50
stdhealamount = 4
lightningrange = 7
lightningdamage = 20
confusionduration = 6
fireballradius = 3
fireballdamage = 12
check = True
minddraindamage = 7

libtcod.console_set_custom_font('celtic_garamond_10x10_gs_tc.png',libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH,panelheight)
gamemsgs = []
fov_map = libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)

class Object:
	#this is any object, player, monster, item, etc.
	def __init__(self, x, y,char,name,color,blocks = False,fighter = None,item = None):
		self.name = name
		self.blocks = blocks
		self.x = x
		self.y = y
		self.char = char
		self.color = color
		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self
		self.item = item
		if self.item:
			self.item.owner = self
	def move(self, dx, dy):
		if not is_blocked(self.x+dx,self.y+dy):
			self.x += dx
			self.y += dy
	def draw(self):
		if libtcod.map_is_in_fov(fov_map,self.x,self.y):
			libtcod.console_set_default_foreground(con,self.color)
			libtcod.console_put_char(con,self.x,self.y, self.char,libtcod.BKGND_NONE)
	def clear(self):
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)
	def movetowards(self,targetx,targety):
		dx = targetx-self.x
		dy = targety-self.y
		distance = math.sqrt(dx ** 2 + dy ** 2)
		dx = int(round(dx/distance))
		dy = int(round(dy/distance))
		self.move(dx,dy)
	def distance_to(self,target):
		return math.sqrt((target.x-self.x)**2+(target.y-self.y)**2)
	def sendtoback(self):
		global objects
		objects.remove(self)
		objects.insert(0,self)
	def distance(self,x,y):
		return math.sqrt((x-self.x)**2+(y-self.y)**2)
class ConfusedMonster:
	def __init__(self,oldai,turns = confusionduration):
		self.oldai = oldai
		self.turns = turns
		self.owner = None
	def turnaction(self):
		self.turns -= 1
		if self.turns == 0:
			self.owner.ai = self.oldai
		else:
			self.owner.owner.move(libtcod.random_get_int(0,-1,1),libtcod.random_get_int(0,-1,1))
class BasicMonster:
	def __init__(self):
		global fov_map
		self.pathtoplayer = libtcod.path_new_using_map(fov_map)
	def turnaction(self):
		monster = self.owner
		libtcod.path_compute(self.pathtoplayer,monster.owner.x,monster.owner.y,player.x,player.y)
		if monster.active:
			if monster.owner.distance_to(player) >= 2:
				x,y = libtcod.path_walk(self.pathtoplayer,False)
				monster.owner.movetowards(x,y)
			elif player.fighter.hp > 0:
				monster.attack(player)
		elif libtcod.random_get_int(0,0,100) == 100 and monster.owner.distance_to(player) > 20:
			message('you hear a growl')
		else:
			monster.owner.move(libtcod.random_get_int(0,-1,1),libtcod.random_get_int(0,-1,1))
class Fighter:
	def __init__(self,hp,defense,power,deathfunction = None,speed = 1,ai = None,magic = 10,magicpower = 1):
		self.active = False
		self.maxhp = hp
		self.hp = hp
		self.defense = defense
		self.power = power
		self.deathfunction = deathfunction
		self.speed = speed
		self.movement = speed
		self.ai = ai
		if self.ai:
			self.ai.owner = self
		self.magic = magic
		self.maxmagic = magic
		self.magicpower = magicpower
	def takedamage(self,damage):
		self.hp -= damage
		self.active = True
		if self.hp <= 0:
			function = self.deathfunction
			if function is not None:
				function(self.owner)
	def attack(self,target):
		damage = self.power - target.fighter.defense
		if damage > 0:
			message('The ' + self.owner.name + ' attacks ' + target.name)
			target.fighter.takedamage(damage)
		else:
			message('The ' + self.owner.name + ' attacks ' + target.name + ' in vain')
	def heal(self,value):
		self.hp += value
		if self.hp > self.maxhp:
			self.hp = self.maxhp
	def taketurn(self):
		monster = self.owner
		if monster.distance_to(player) < 5:
			self.active = True
		if self.speed >= 1:
			for c in range(0,self.speed):
				if self.ai is not None:
					self.ai.turnaction()
		elif self.speed < 1:
			if self.movement >= 1 and self.ai is not None:
				self.ai.turnaction()
				self.movement = self.speed
			else:
				self.movement += self.speed

def playerdeath(player):
	global gamestate
	message('You Died')
	gamestate = 'dead'
	player.char = '%'
	player.color = libtcod.dark_red
	
def monsterdeath(monster):
	message('The ' + monster.name + ' dies')
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = monster.name + ' corpse'
	monster.sendtoback()

def closestmonster(maxrange):
	closestenemy = None
	closestdist = maxrange+1
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map,object.x,object.y):
			dist = player.distance_to(object)
			if dist < closestdist:
				closestenemy = object
				closestdist = dist
	return closestenemy
			
class Item:
	def __init__(self,usefunction = None,consumable = True):
		self.usefunction = usefunction
	def pickup(self):
		if len(inventory) >= 26:
			message('You cannot carry anymore')
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You pick up the ' + self.owner.name)
	def use(self):
		if self.usefunction is None:
			message('the ' + self.owner.name + ' cannot be used')
		else:
			self.usefunction()
	
class Spell:
	def __init__(self,name,cost,castfunction = None):
		self.castfunction = castfunction
		self.name = name
		self.cost = cost
	def learn(self):
		global check
		if len(spells) >= 26:
			message('You cannot know any more spells')
			check = True
			return True
		for spell in spells:
			if spell.name == self.name:
				message('You already know this spell')
				check = True
				return True
		spells.append(self)
		message('You learned ' + self.name + '!')
		check = False
	def cast(self):
		if player.fighter.magic >= self.cost:
			self.castfunction()
			if check == False:
				player.fighter.magic -= self.cost
		
	
class Tile:
	def __init__(self,blocked,block_sight = None):
		self.blocked = blocked
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight
		self.explored = False

class Rect:
	def __init__(self,x,y,w,h):#x and y are the start coords, w and h are the width and height
		self.x1 = x
		self.y1 = y
		self.x2 = x+w
		self.y2 = y+h
	def center(self):
		centerx = (self.x1+self.x2)/2
		centery = (self.y1+self.y2)/2
		return (centerx,centery)
	def intersect(self,other):
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)
def create_room(room):
	global map
	for x in range(room.x1,room.x2+1):
		for y in range(room.y1+1,room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False
def createhtunnel(x1,x2,y):
	global map
	for x in range(min(x1,x2),max(x1,x2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
def createvtunnel(y1,y2,x):
	global map
	for y in range(min(y1,y2),max(y1,y2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def targettile(maxrange = None):
	global key, mouse
	while True:
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()
		(x,y) = (mouse.cx,mouse.cy)
		if mouse.lbutton_pressed:
			return (x,y)
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			return (None,None)
		
def menu(header,options,width):
	if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options')
	headerheight = libtcod.console_get_height_rect(con,0,0,width,SCREEN_HEIGHT,header)
	height = len(options) + headerheight
	window = libtcod.console_new(width,height)
	libtcod.console_set_default_foreground(window,libtcod.white)
	libtcod.console_print_rect_ex(window,0,0,width,height,libtcod.BKGND_NONE,libtcod.LEFT,header)
	y = headerheight
	letter_index = ord('a')
	for optiontext in options:
		text = '('+chr(letter_index)+') '+optiontext
		libtcod.console_print_ex(window,0,y,libtcod.BKGND_NONE,libtcod.LEFT,text)
		y += 1
		letter_index += 1
	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(window,0,0,width,height,0,x,y,1.0,0.7)
	libtcod.console_flush()
	while not libtcod.console_wait_for_keypress(True):
		True
	key = libtcod.console_wait_for_keypress(True)
	index = key.c - ord('a')
	if index >= 0 and index < len(options):return index
	return None
def inventorymenu(header):
	if len(inventory) == 0:
		options = ['Inventory is empty']
	else:
		options = [item.name for item in inventory]
	index = menu(header,options,inventorywidth)
	if index is None or len(inventory) == 0: return None
	return index
def spellmenu(header):
	if len(spells) == 0:
		options = ['No spells known']
	else:
		options = [spell.name for spell in spells]
	index = menu(header,options,inventorywidth)
	if index is None or len(spells) == 0: return None
	return index
	
def castheal():
	global check
	#print 'castheal'
	exitstatus = None
	if player.fighter.hp == player.fighter.maxhp:
		message('You are already at full health')
		exitstatus = True
		#print 'exitstatus = ' + str(exitstatus)
		check = exitstatus
		return exitstatus
	message('Your wounds close',libtcod.light_violet)
	player.fighter.heal(stdhealamount)
	exitstatus = False
	#print 'exitstatus = ' + str(exitstatus)
	check = exitstatus
	return exitstatus
def castlightning():
	global check
	#print 'castlightning'
	exitstatus = None
	monster = closestmonster(lightningrange)
	if monster is None:
		message('No enemy close enough')
		exitstatus = True
		#print 'exitstatus = ' + str(exitstatus)
		check = exitstatus
		return True
	message('a lightning bolt strikes the ' + monster.name + ' with a loud thunderclap',libtcod.light_blue)
	monster.fighter.takedamage(lightningdamage)
	exitstatus = False
	#print 'exitstatus = ' + str(exitstatus)
	check = exitstatus
	return False
def castconfuse():	
	global check
	#print 'castconfuse'
	exitstatus = None
	monster = closestmonster(lightningrange)
	if monster is None:
		message('No enemy close enough')
		exitstatus = True
		#print 'exitstatus = ' + str(exitstatus)
		check = exitstatus
		return True
	message('The ' + monster.name + ' goes insane!',libtcod.light_blue)
	monster.fighter.ai = ConfusedMonster(monster.fighter.ai)
	monster.fighter.ai.owner = monster.fighter
	exitstatus = False
	#print 'exitstatus = ' + str(exitstatus)
	check = exitstatus
	return False
def castfireball():
	global check
	#print 'castfireball'
	exitstatus = None
	message('Left-click a tile to target the fireball, right-click to cancel.',libtcod.light_cyan)
	(x,y) = targettile()
	if x is None:
		exitstatus = True
		#print 'exitstatus = ' + str(exitstatus)
		check = exitstatus
		return True
	message('The fireball explodes!',libtcod.orange)
	for obj in objects:
		if obj.distance(x,y) <= fireballradius and obj.fighter:
			message('The ' + obj.name + ' gets burned!', libtcod.orange)
			obj.fighter.takedamage(fireballdamage)
	exitstatus = False
	#print 'exitstatus = ' + str(exitstatus)
	check = exitstatus
	return False
def castminddrain():
	global check
	monster = closestmonster(7)
	if monster is None:
		check = True
		return 'cancelled'
	if monster.fighter.magic > 0:
		monster.fighter.magic -= minddraindamage
		if monster.fighter.magic < 0:
			diff = 0 - monster.fighter.magic
			monster.fighter.magic = 0
			player.fighter.magic += minddraindamage - diff
			
		else:
			player.fighter.magic += minddraindamage
def learnlightning():
	lightning.learn()
def learnconfuse():
	confuse.learn()
def learnfireball():
	fireball.learn()
def learnheal():
	heal.learn()
	
player = Object(25,23, '@',"player",libtcod.white,None,Fighter(30,2,5,playerdeath,ai = None,magic = 30,magicpower = 5))
#npc = Object(SCREEN_WIDTH/2-5,SCREEN_HEIGHT/2, 'M', libtcod.white)
objects = [player]
inventory = []
spells = []	
rooms = []
num_rooms = 0
fov_recompute = True
lightning = Spell('Lightning',5,castfunction = castlightning)
fireball = Spell('Fireball',3,castfunction = castfireball)
confuse = Spell('Confuse',2,castfunction = castconfuse)
heal = Spell('Heal',2,castfunction = castheal)

def makegoblin(x,y):
	return Object(x,y,'g',"Goblin",libtcod.desaturated_green,True,Fighter(10,0,3,monsterdeath,speed = 2,ai = BasicMonster()))
def makeogre(x,y):
	return Object(x,y,'O',"Ogre",libtcod.darker_green,True,Fighter(16,1,4,monsterdeath,speed = 0.5,ai = BasicMonster()))
def makehealpotion(x,y):
	return Object(x,y,'!','Healing potion',libtcod.violet,item = Item(usefunction = castheal))
def makelightningscroll(x,y):
	return Object(x,y,'#','Lightning scroll',libtcod.light_yellow,item = Item(usefunction = learnlightning))
def makeconfusescroll(x,y):
	return Object(x,y,'#','Confuse scroll',libtcod.light_yellow,item = Item(usefunction = learnconfuse))
def makefireballscroll(x,y):
	return Object(x,y,'#','Fireball scroll',libtcod.light_yellow,item = Item(usefunction = learnfireball))
def makehealscroll(x,y):
	return Object(x,y,'#','Heal scroll',libtcod.light_yellow,item = Item(usefunction = learnheal))
	
def placeobjects(room):
	num_monsters = libtcod.random_get_int(0,0,MAX_ROOM_MONSTERS)
	for i in range(num_monsters):
		x = libtcod.random_get_int(0,room.x1+1,room.x2-1)
		y = libtcod.random_get_int(0,room.y1+1,room.y2-1)
		if libtcod.random_get_int(0,0,100) > 80:
			monster = makegoblin(x,y)
			objects.append(monster)
		elif libtcod.random_get_int(0,0,100) > 80:
			monster = makeogre(x,y)
			objects.append(monster)
	numitems = libtcod.random_get_int(0,0,MAXROOMITEMS)
	for i in range(numitems):
		x = libtcod.random_get_int(0,room.x1+1,room.x2-1)
		#print str(x)
		#print str(room.x1) + ' ' + str(room.x2)
		y = libtcod.random_get_int(0,room.y1+1,room.y2-1)
		#print str(y)
		#print str(room.y1) + ' ' + str(room.y2)
		if is_blocked(x,y) == False:
			dice = libtcod.random_get_int(0,0,110)
			if dice < 70:
				item = makehealpotion(x,y)
			elif dice < 80:
				item = makelightningscroll(x,y)
			elif dice < 90:
				item = makefireballscroll(x,y)
			elif dice < 100:
				item = makehealscroll(x,y)
			else:
				item = makeconfusescroll(x,y)
			objects.append(item)
			#print item.name
			item.sendtoback()

def make_map():
	global map
	global rooms
	global num_rooms
	map = [[Tile(True)
		for y in range(MAP_HEIGHT)]
			for x in range(MAP_WIDTH)]
	for r in range(MAX_ROOMS):
		w = libtcod.random_get_int(0,MIN_ROOM_SIZE,MAX_ROOM_SIZE)
		h = libtcod.random_get_int(0,MIN_ROOM_SIZE,MAX_ROOM_SIZE)
		x = libtcod.random_get_int(0,0,MAP_WIDTH-w-1)
		y = libtcod.random_get_int(0,0,MAP_HEIGHT-h-1)
		newroom = Rect(x,y,w,h)
		failed = False
		for otherroom in rooms:
			if newroom.intersect(otherroom):
				failed = True
				break
		if not failed:
			create_room(newroom)
			(new_x,new_y) = newroom.center()
			if num_rooms == 0:
				player.x = new_x
				player.y = new_y
			else:
				(prevx,prevy) = rooms[num_rooms-1].center()
				if libtcod.random_get_int(0,0,1) == 1:
					createhtunnel(prevx,new_x,prevy)
					createvtunnel(prevy,new_y,new_x)
				else:
					createvtunnel(prevy,new_y,prevx)
					createhtunnel(prevx,new_x,new_y)
			placeobjects(newroom)
			rooms.append(newroom)
			num_rooms += 1
			
def is_blocked(x,y):
	if x >= MAP_WIDTH or x <= 0 or y >= MAP_HEIGHT or y <= 0:
		return True
	elif map[x][y].blocked:
		return True
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True
	return False
			
make_map()

def message(newmsg,color=libtcod.white):
	newmsglines = textwrap.wrap(newmsg,msgwidth)
	for line in newmsglines:
		if len(gamemsgs) == msgheight:
			del gamemsgs[0]
		gamemsgs.append((line,color))
			
def handle_keys():
	global key
	global check
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'
	if gamestate == 'playing':
		if key.vk == libtcod.KEY_UP:
			playermoveorattack(0,-1)
		elif key.vk == libtcod.KEY_DOWN:
			playermoveorattack(0,1)
		elif key.vk == libtcod.KEY_LEFT:
			playermoveorattack(-1,0)
		elif key.vk == libtcod.KEY_RIGHT:
			playermoveorattack(1,0)
		else:
			keychar = chr(key.c)
			if keychar == 'g':
				for object in objects:
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pickup()
						break
			if keychar == 'i':
				chosen = inventorymenu('press the key next to the item to use it')
				if chosen is not None:
					#print inventory[chosen].name
					#print 'check = ' + str(check)
					inventory[chosen].item.use()
					#print 'check = ' + str(check)
					if check == False:
						del inventory[chosen]
					return 'didnttaketurn'
			if keychar == 's':
				chosen = spellmenu('press the key next to the spell to cast it')
				if chosen is not None:
					spells[chosen].cast()
				return 'castedspell'
			if keychar == 'o':
				for obj in objects:
					print(obj.name + ' ' + str(obj.x) + ' ' + str(obj.y))
				return 'didnttaketurn'
			return 'didnttaketurn'

def playermoveorattack(dx,dy):
	global fov_recompute
	x = player.x+dx
	y = player.y+dy
	target = None
	for object in objects:
		if object.x == x and object.y == y and object.fighter != None:
			target = object
			break
	if target is not None:
		player.fighter.attack(target)
	else:
		player.move(dx,dy)
		fov_recompute = True
		
def render_all():
	global fov_recompute
	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map,player.x,player.y,TORCH_RADIUS,FOV_LIGHT_WALLS,FOV_ALGO)
	for Object in objects:
		if Object != player:
			Object.draw()
			
	player.draw()
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			wall = map[x][y].block_sight
			visible = libtcod.map_is_in_fov(fov_map,x,y)
			if not visible:
				if map[x][y].explored:
					if wall:
						libtcod.console_set_char_background(con,x,y,color_dark_wall,libtcod.BKGND_SET)
					else:
						libtcod.console_set_char_background(con,x,y,color_dark_ground,libtcod.BKGND_SET)
			else:
				map[x][y].explored = True
				if wall:
					libtcod.console_set_char_background(con,x,y,color_light_wall,libtcod.BKGND_SET)
				else:
					libtcod.console_set_char_background(con,x,y,color_light_ground,libtcod.BKGND_SET)
	libtcod.console_blit(con, 0, 0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0)
	libtcod.console_set_default_background(panel,libtcod.black)
	libtcod.console_clear(panel)
	y = 1
	for (line,color) in gamemsgs:
		libtcod.console_set_default_foreground(panel,color)
		libtcod.console_print_ex(panel,msgx,y,libtcod.BKGND_NONE,libtcod.LEFT,line)
		y+=1
	renderbar(1,1,BAR_WIDTH,'HP',player.fighter.hp,player.fighter.maxhp,libtcod.light_red,libtcod.darker_red)
	renderbar(1,2,BAR_WIDTH,'MP',player.fighter.magic,player.fighter.maxmagic,libtcod.light_blue,libtcod.darker_blue)
	libtcod.console_set_default_foreground(panel,libtcod.light_gray)
	libtcod.console_print_ex(panel,1,0,libtcod.BKGND_NONE,libtcod.LEFT,getnameundermouse())
	libtcod.console_blit(panel,0,0,SCREEN_WIDTH,panelheight,0,0,panely)
	
def renderbar(x,y,totalwidth,name,value,maximum,barcolor,backcolor):

	barwidth = int(float(value)/maximum*totalwidth)
	libtcod.console_set_default_background(panel,backcolor)
	libtcod.console_rect(panel,x,y,totalwidth,1,False,libtcod.BKGND_SCREEN)
	libtcod.console_set_default_background(panel,barcolor)
	if barwidth > 0:
		libtcod.console_rect(panel,x,y,barwidth,1,False,libtcod.BKGND_SCREEN)
	libtcod.console_set_default_foreground(panel,libtcod.white)
	libtcod.console_print_ex(panel,x+totalwidth/2,y,libtcod.BKGND_NONE,libtcod.CENTER,name + ': ' + str(value) + '/' + str(maximum))
	
def getnameundermouse():
		global mouse
		(x,y) = (mouse.cx,mouse.cy)
		names = [obj.name for obj in objects if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map,obj.x,obj.y)]
		names = ', '.join(names)
		return names
	
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map,x,y,not map[x][y].block_sight,not map[x][y].blocked)

message('Greetings, puny mortal!')	
mouse = libtcod.Mouse()
key = libtcod.Key()

while not libtcod.console_is_window_closed():
	libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
	render_all()
	libtcod.console_flush()
	for Object in objects:
		Object.clear()
	player_action = handle_keys()
	if player_action == 'exit':
		break
	if gamestate == 'playing' and player_action != 'didnttaketurn':
		for Object in objects:
			if Object.fighter:
				Object.fighter.taketurn()
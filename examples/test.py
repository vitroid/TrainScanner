#test video generator for NodeBox.app
#40 frames (1 sec)

speed(100)
size(200,200)
vx=-40
x=250
vy=1
y=100

def draw():
    global vx,vy,x,y
    fontsize(100)
    text("TrainScanner",x,y)
    x += vx
    y += vy
    vx += 1
    

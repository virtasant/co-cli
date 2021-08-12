class DDBStreamParser():

    def __init__(self):
        self.a_eb_arn = self.update_notification_target()
        
    # overwrite in child
    def update_notification_target(self):
        return None

    def handle_insert(self, record):
        print("Handling INSERT Event")
        return record['NewImage']
        
    def handle_delete(self, record):
        print("Handling DELETE Event")
        return record['OldImage']

    def handle_update(self, record):
        print("Handling UPDATE Event")
        new_image = record['NewImage']
        old_image = record['OldImage']
        return dict_diff(old_image, new_image)
        
    def process(self, event):
    	try:
    		for record in event['Records']:
    			dynamodb = record['dynamodb']
    			if record['eventName'] == 'INSERT':
    				self.handle_insert(dynamodb)
    			elif record['eventName'] == 'MODIFY':
    				self.handle_update(dynamodb)
    			elif record['eventName'] == 'REMOVE':
    				self.handle_delete(dynamodb)
    	except Exception as e: 
    		print(e)
        
###################################################################

def dict_diff(a, b):
    d = {}
    for i in [key for key in a.keys() & b if a[key] != b[key]]:
       d.update({i:b[i]})
    return d if bool(d) else None

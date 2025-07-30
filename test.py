import numpy as np

# Save
dictionary = {'hello':'world'}
np.save('my_file.npy', dictionary) 

# Load
read_dictionary = np.load('my_file.npy',allow_pickle='TRUE').item()
print(read_dictionary['hello']) # displays "world"

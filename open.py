import pickle

# Replace 'file.pkl' with your actual filename and path
with open('book.pkl', 'rb') as file:
    data = pickle.load(file)

print(data)

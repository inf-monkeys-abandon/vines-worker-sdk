from vines_worker_sdk.utils import convert_csv_to_json

if __name__ == '__main__':
    csv_file = "./test.csv"
    data = convert_csv_to_json(csv_file)
    print(data)

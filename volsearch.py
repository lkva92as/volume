import json
import urllib3

http = urllib3.PoolManager()

def load_pi_data():
    headers = {'Connection': 'keep-alive', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:57.0) Gecko/20100101 Firefox/57.0', 'Accept-Language': 'en-US,en;q=0.5', 'Referer': 'https://www.predictit.org/Browse/Featured'}
    pi_request = http.request('GET','http://www.predictit.org/api/marketdata/all', headers=headers)
    pi_data = json.loads(pi_request.data.decode('utf-8'))['markets']
    return pi_data
    
def load_stats(id):
    headers = {'Connection': 'keep-alive', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:57.0) Gecko/20100101 Firefox/57.0', 'Accept-Language': 'en-US,en;q=0.5', 'Referer': 'https://www.predictit.org/Browse/Featured'}
    stats_url = "https://www.predictit.org/api/Market/" + str(id) + "/Contracts/Stats"
    stats_request = http.request('GET', stats_url, headers=headers)
    stats_data = json.loads (stats_request.data.decode('utf-8'))
    return stats_data

def place_value(number): 
    return ("{:,}".format(number))
    
def scale_up(number):
    return 0 if number is None else int(number*100)

def lambda_handler(event, context):

    slack_event = event['queryStringParameters']
    text = slack_event['text']
    response_url = slack_event['response_url']

    data = {
        'response_type': 'in_channel',
        'text': 'Checking, please wait...'
    }
    
    encoded_data = json.dumps(data).encode('utf-8')
    r = http.request('POST', response_url, body=encoded_data, headers={'Content-Type': 'application/json'})
    
    
    response = ""

    pi_data = load_pi_data()
    
    markets = []
    contracts = []
    new_contracts = []

    name_length = 3
    
    for market in pi_data:
        if text.lower() in market["shortName"].lower() + market["name"].lower():
            markets.append(market)
            pi_data.remove(market)
            for contract in market["contracts"]:
                contract['lastTradePrice'] = scale_up(contract['lastTradePrice'])
                contract['lastClosePrice'] = scale_up(contract['lastClosePrice'])
                contract['bestBuyYesCost'] = scale_up(contract['bestBuyYesCost'])
                contract['bestSellYesCost'] = scale_up(contract['bestSellYesCost'])
                if market['name'] != contract['name']:
                    name_length = max(name_length, len(contract['shortName']))
                else:
                    contract['shortName'] = "Yes"
                
        else:
            for contract in market["contracts"]:
                if text.lower() in contract["name"].lower() + contract["shortName"].lower():
                    market["contracts"] = [contract]
                    name_length = max(name_length, len(contract['shortName']))
                    contracts.append(market)
    
    all_markets = markets + contracts
    
    # for formatting
    open_length = 1
    today_length = 1
    
    for market in all_markets:
        if len(all_markets) < 10:
            market_stats = load_stats(market['id'])
            # print(market_stats)
            for stats_item in market_stats:
                for contract in market['contracts']:
                    if contract['id'] == stats_item['contractId']:
                        # contract['totalSharesTraded'] = stats_item['totalSharesTraded']
                        contract['todaysVolume'] = place_value(stats_item['todaysVolume'])
                        today_length = max(len(str(contract['todaysVolume'])), today_length)
                        contract['openInterest'] = place_value(stats_item['openInterest'])
                        open_length = max(len(str(contract['openInterest'])), open_length)
        
        response += "<" + market['url'] + "|" + market['name'] +">\n"
        
        for contract in market["contracts"]:
                
            response += "`"
            response += contract['shortName'].ljust(name_length+2, ' ')
        
            response += " " + str(contract['lastTradePrice']).rjust(2,' ') + "  "
            
            # create change if applicable
            if contract['lastClosePrice'] > 0:
                change = contract['lastTradePrice'] - contract['lastClosePrice']
                
            if change > 0:
                response += str("↑" + str(change)).rjust(3,' ')
            elif change < 0:
                response += str("↓" + str(abs(change))).rjust(3,' ')
            else:
                response += "---"
            
            response += "    Buy " + str(contract['bestBuyYesCost']).rjust(2,' ') + "    Sell " + str(contract['bestSellYesCost']).rjust(2,' ')
            
            if len(all_markets) < 10:
                response += "    Shares " + str(contract['openInterest']).rjust(open_length, ' ') + "   Today " + str(contract['todaysVolume']).rjust(today_length, ' ')
                
            
        
            response += "`\n"
        
        # response += "\n" + market['url']
        # for contract in market["contracts"]:
        #     response += "\n" + contract['name']
        
    # print(response)
    
    data = {
        'response_type': 'in_channel',
        'text': response
    }
    
    # requests.post(response_url, json=data)
    
    return data

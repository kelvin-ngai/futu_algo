#  Copyright (c)  billpwchan - All Rights Reserved
#  Unauthorized copying of this file, via any medium is strictly prohibited
#   Proprietary and confidential
#   Written by Bill Chan <billpwchan@hotmail.com>, 2021
import pandas as pd
import talib as talib

import logger
from strategies.Strategies import Strategies

pd.options.mode.chained_assignment = None  # default='warn'
talib.set_compatibility(1)


class KDJCross(Strategies):
    def __init__(self, input_data: dict, fast_k=9, slow_k=3, slow_d=3, observation=100):
        self.FAST_K = fast_k
        self.SLOW_K = slow_k
        self.SLOW_D = slow_d
        self.OBSERVATION = observation
        self.default_logger = logger.get_logger("kdj_cross")

        super().__init__(input_data)
        self.parse_data()

    def parse_data(self, latest_data: pd.DataFrame = None):
        # Received New Data => Parse it Now to input_data
        if latest_data is not None:
            # Only need to update MACD for the stock_code with new data
            stock_list = [latest_data['code'][0]]

            # Remove records with duplicate time_key. Always use the latest data to override
            time_key = latest_data['time_key'][0]
            self.input_data[stock_list[0]].drop(
                self.input_data[stock_list[0]][self.input_data[stock_list[0]].time_key == time_key].index,
                inplace=True)
            # Append empty columns and concat at the bottom
            latest_data = pd.concat([latest_data, pd.DataFrame(columns=['%k', '%d', '%j'])])
            self.input_data[stock_list[0]] = self.input_data[stock_list[0]].append(latest_data)
        else:
            stock_list = self.input_data.keys()

        # Calculate EMA for the stock_list
        for stock_code in stock_list:
            # Need to truncate to a maximum length for low-latency
            self.input_data[stock_code] = self.input_data[stock_code].iloc[-self.OBSERVATION:]
            self.input_data[stock_code][['open', 'close', 'high', 'low']] = self.input_data[stock_code][
                ['open', 'close', 'high', 'low']].apply(pd.to_numeric)

            low = self.input_data[stock_code]['low'].rolling(9, min_periods=9).min()
            low.fillna(value=self.input_data[stock_code]['low'].expanding().min(), inplace=True)
            high = self.input_data[stock_code]['high'].rolling(9, min_periods=9).max()
            high.fillna(value=self.input_data[stock_code]['high'].expanding().max(), inplace=True)
            rsv = (self.input_data[stock_code]['close'] - low) / (high - low) * 100

            self.input_data[stock_code]['%k'] = pd.DataFrame(rsv).ewm(com=2).mean()
            self.input_data[stock_code]['%d'] = self.input_data[stock_code]['%k'].ewm(com=2).mean()
            self.input_data[stock_code]['%j'] = 3 * self.input_data[stock_code]['%k'] - \
                                                2 * self.input_data[stock_code]['%d']

            self.input_data[stock_code].reset_index(drop=True, inplace=True)
            self.default_logger.info(self.input_data[stock_code])

    def buy(self, stock_code) -> bool:
        # Crossover of EMA Fast with other two EMAs
        current_record = self.input_data[stock_code].iloc[-1]
        last_record = self.input_data[stock_code].iloc[-2]
        # Buy Decision based on EMA-Fast exceeds both other two EMAs (e.g., 5-bar > 8-bar and 13-bar)
        buy_decision = True

        if buy_decision:
            self.default_logger.info(
                f"Buy Decision: {current_record['time_key']} based on \n {pd.concat([last_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")

        return buy_decision

    def sell(self, stock_code) -> bool:
        # Crossover of EMA Fast with other two EMAs
        current_record = self.input_data[stock_code].iloc[-1]
        last_record = self.input_data[stock_code].iloc[-2]
        # Sell Decision based on EMA-Fast drops below either of the two other EMAs(e.g., 5-bar < 8-bar or 13-bar)
        sell_decision = True
        if sell_decision:
            self.default_logger.info(
                f"Sell Decision: {current_record['time_key']} based on \n {pd.concat([last_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")
        return sell_decision

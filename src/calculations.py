import pandas as pd

def calculate_hours_per_project(data):
    """Calculates total hours per project for each user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    hours = []
    for (user, project), group in data.groupby(['user', 'project']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        # Ensure start_times and stop_times have the same length
        min_length = min(len(start_times), len(stop_times))
        total_hours = (stop_times.iloc[:min_length].values - start_times.iloc[:min_length].values).sum().astype('timedelta64[h]').astype(int)
        hours.append({'user': user, 'project': project, 'total_hours': total_hours})
    return pd.DataFrame(hours)

def calculate_total_hours_per_user(data):
    """Calculates total hours per user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    start_date = data['timestamp'].min().strftime("%d-%m-%Y %H:%M:%S")
    end_date = data['timestamp'].max().strftime("%d-%m-%Y %H:%M:%S")
    date_range = f"{start_date} - {end_date}"
    total_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        # Ensure start_times and stop_times have the same length
        min_length = min(len(start_times), len(stop_times))
        total_hours_user = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 for i in range(min_length))
        total_hours.append({'user': user, 'total_hours': total_hours_user})
    return pd.DataFrame(total_hours), date_range

def calculate_average_hours_per_user(data):
    """Calculates average hours per user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_hours_user = (stop_times.values - start_times.values).sum().astype('timedelta64[h]').astype(int)
        average_hours_user = total_hours_user / len(group['date'].unique())
        average_hours.append({'user': user, 'average_hours': average_hours_user})
    return pd.DataFrame(average_hours)

def calculate_average_hours_per_period(data, period_days):
    """Calculates average hours per user for a given period in days."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        min_length = min(len(start_times), len(stop_times))
        total_hours = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 for i in range(min_length))
        
        # Calculate the number of days the user has data for
        num_days = len(group['date'].unique())
        
        # Ensure that the number of periods is at least 1
        num_periods = max(1, num_days / period_days)
        
        average_hours_user = total_hours / num_periods
        average_hours.append({'user': user, 'average_hours': average_hours_user, 'period_days': period_days})
    return pd.DataFrame(average_hours)

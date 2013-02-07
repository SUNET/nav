#
# Copyright (C) 2009, 2011 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# NAV. If not, see <http://www.gnu.org/licenses/>.
#

from IPy import IP
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.datastructures import SortedDict

from nav.models.manage import Arp, Cam

from nav import asyncdns

from nav.web.machinetracker import forms, iprange
from nav.web.machinetracker.utils import hostname, from_to_ip, ip_dict
from nav.web.machinetracker.utils import process_ip_row, track_mac, get_prefix_info
from nav.web.machinetracker.utils import (min_max_mac, ProcessInput,
                                          normalize_ip_to_string)

NAVBAR = [('Home', '/'), ('Machinetracker', None)]
IP_TITLE = 'NAV - Machinetracker - IP Search'
MAC_TITLE = 'NAV - Machinetracker - MAC Search'
SWP_TITLE = 'NAV - Machinetracker - Switch Search'
IP_DEFAULTS = {'title': IP_TITLE, 'navpath': NAVBAR, 'active': {'ip': True}}
MAC_DEFAULTS = {'title': MAC_TITLE, 'navpath': NAVBAR, 'active': {'mac': True}}
SWP_DEFAULTS = {'title': SWP_TITLE, 'navpath': NAVBAR, 'active': {'swp': True}}

ADDRESS_LIMIT = 4096 # Value for when inactive gets disabled


def ip_search(request):
    if request.GET.has_key('ip_range') or request.GET.has_key('prefixid'):
        return ip_do_search(request)
    info_dict = {
        'form': forms.IpTrackerForm(),
    }
    info_dict.update(IP_DEFAULTS)
    return render_to_response(
        'machinetracker/ip_search.html',
        info_dict,
        RequestContext(request)
    )

def ip_do_search(request):
    input = ProcessInput(request.GET).ip()
    form = forms.IpTrackerForm(input)
    tracker = None
    form_data = {}
    row_count = 0
    from_ip = None
    to_ip = None

    if form.is_valid():
        ip_range = form.cleaned_data['ip_range']
        dns = form.cleaned_data['dns']
        active = form.cleaned_data['active']
        inactive = form.cleaned_data['inactive']
        days = form.cleaned_data['days']
        form_data = form.cleaned_data
        
        from_ip, to_ip = (ip_range[0], ip_range[-1])

        if (to_ip.int()-from_ip.int()) > ADDRESS_LIMIT:
            inactive = False

        from_time = date.today() - timedelta(days=days)

        row_count = 0
        ip_result = SortedDict()
        result = Arp.objects.filter(
            end_time__gt=from_time,
        ).extra(
            where=['ip BETWEEN %s and %s'],
            params=[unicode(from_ip), unicode(to_ip)]
        ).order_by('ip', 'mac', '-start_time')

        ip_result = ip_dict(result)

        if inactive:
            ip_range = [IP(ip) for ip in range(from_ip.int(), to_ip.int() + 1)]
        else:
            ip_range = [key for key in ip_result]
       
        if dns:
            ips_to_lookup = [str(ip) for ip in ip_range]
            dns_lookups = asyncdns.reverse_lookup(ips_to_lookup)
        
        tracker = SortedDict()

        for ip_key in ip_range:
            ip = unicode(ip_key)
            if active and ip_key in ip_result:
                rows = ip_result[ip_key]
                for row in rows:
                    row = process_ip_row(row, dns=False)
                    if dns:
                        if (isinstance(dns_lookups[ip], Exception)
                            or not dns_lookups[ip]):
                            row.dns_lookup = ""
                        else:
                            row.dns_lookup = dns_lookups[ip][0]
                    row.ip_int_value = normalize_ip_to_string(row.ip)
                    if (row.ip, row.mac) not in tracker:
                        tracker[(row.ip, row.mac)] = []
                    tracker[(row.ip, row.mac)].append(row)
            elif inactive and ip_key not in ip_result:
                row = {'ip': ip}
                row['ip_int_value'] = normalize_ip_to_string(ip)
                if dns:
                    if not isinstance(dns_lookups[ip], Exception):
                        row['dns_lookup'] = dns_lookups[ip][0]
                    else:
                        row['dns_lookup'] = ""
                tracker[(ip, "")] = [row]

        row_count = sum(len(mac_ip_pair) for mac_ip_pair in tracker.values())

    # If the form was valid, but we found no results, display error message
    display_no_results = False
    if form.is_valid() and not row_count:
        display_no_results = True

    info_dict = {
        'form': form,
        'form_data': form_data,
        'ip_tracker': tracker,
        'ip_tracker_count': row_count,
        'subnet_start': unicode(from_ip),
        'subnet_end': unicode(to_ip),
        'display_no_results': display_no_results,
    }
    info_dict.update(IP_DEFAULTS)
        
    return render_to_response(
        'machinetracker/ip_search.html',
        info_dict,
        RequestContext(request)
    )

def mac_search(request):
    if request.GET.has_key('mac'):
        return mac_do_search(request)
    info_dict = {
        'form': forms.MacTrackerForm()
    }
    info_dict.update(MAC_DEFAULTS)
    return render_to_response(
        'machinetracker/mac_search.html',
        info_dict,
        RequestContext(request)
    )

def mac_do_search(request):
    input = ProcessInput(request.GET).mac()
    form = forms.MacTrackerForm(input)
    info_dict = {
        'form': form,
        'form_data': None,
        'mac_tracker': None,
        'ip_tracker': None,
        'mac_tracker_count': 0,
        'ip_tracker_count': 0,
        'disable_ip_context' : True,
    }
    if form.is_valid():
        mac = form.cleaned_data['mac']
        days = form.cleaned_data['days']
        dns = form.cleaned_data['dns']
        from_time = date.today() - timedelta(days=days)

        mac_min, mac_max = min_max_mac(mac)

        cam_result = Cam.objects.select_related('netbox').filter(
            end_time__gt=from_time,
        ).extra(
            where=['mac BETWEEN %s and %s'],
            params=[mac_min, mac_max]
        ).order_by('mac', 'sysname', 'module', 'port', '-start_time').values(
            'sysname', 'module', 'port', 'start_time', 'end_time', 'mac',
            'netbox__sysname'
        )

        arp_result = Arp.objects.filter(
            end_time__gt=from_time,
            mac__range=(mac_min, mac_max)
        ).order_by('mac', 'ip', '-start_time').values(
            'ip', 'mac', 'start_time', 'end_time'
        )

        mac_count = len(cam_result)
        ip_count = len(arp_result)
        mac_tracker = track_mac(('mac', 'sysname', 'module', 'port'),
                                cam_result, dns=False)
        ip_tracker = track_mac(('ip', 'mac'), arp_result, dns)

        info_dict.update({
            'form_data': form.cleaned_data,
            'mac_tracker': mac_tracker,
            'ip_tracker': ip_tracker,
            'mac_tracker_count': mac_count,
            'ip_tracker_count': ip_count,
        })

    info_dict.update(MAC_DEFAULTS)
    return render_to_response(
        'machinetracker/mac_search.html',
        info_dict,
        RequestContext(request)
    )

def switch_search(request):
    if request.GET.has_key('switch'):
        return switch_do_search(request)
    info_dict = {
        'form': forms.SwitchTrackerForm(),
    }
    info_dict.update(SWP_DEFAULTS)
    return render_to_response(
        'machinetracker/switch_search.html',
        info_dict,
        RequestContext(request)
    )

def switch_do_search(request):
    input = ProcessInput(request.GET).swp()
    form = forms.SwitchTrackerForm(input)
    info_dict = {
        'form': form,
        'form_data': None,
        'mac_tracker': None,
        'mac_tracker_count': 0,
    }
    if form.is_valid():
        switch = form.cleaned_data['switch']
        module = form.cleaned_data.get('module')
        port_interface = form.cleaned_data.get('port')
        days = form.cleaned_data['days']
        from_time = date.today() - timedelta(days=days)
        criteria = {}

        if module:
            criteria['module'] = module

        # If port is specified, match on ifindex
        if port_interface:
            try:
                cam_with_ifindex = Cam.objects.filter(
                        Q(sysname__istartswith=switch) |
                        Q(netbox__sysname__istartswith=switch),
                        end_time__gt=from_time,
                        port=port_interface,
                        **criteria
                        ).values('ifindex')[0]
                criteria['ifindex'] = cam_with_ifindex['ifindex']
            except IndexError:
                criteria['port'] = port_interface

        cam_result = Cam.objects.filter(
            Q(sysname__istartswith=switch) |
            Q(netbox__sysname__istartswith=switch),
            end_time__gt=from_time,
            **criteria
        ).order_by('sysname', 'module', 'mac', '-start_time').values(
            'sysname', 'module', 'port', 'start_time', 'end_time', 'mac',
            'netbox__sysname'
        )

        swp_count = len(cam_result)
        swp_tracker = track_mac(('mac', 'sysname', 'module', 'port'),
                                cam_result, dns=False)

        info_dict.update({
            'form_data': form.cleaned_data,
            'mac_tracker': swp_tracker,
            'mac_tracker_count': swp_count,
        })

    info_dict.update(SWP_DEFAULTS)
    return render_to_response(
        'machinetracker/switch_search.html',
        info_dict,
        RequestContext(request)
    )

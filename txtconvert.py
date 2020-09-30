import sys
import os.path, time
import datetime

from dataclasses import dataclass

#DATA STRUCTURE
#Made this to strongly type parsed data
@dataclass
class CanLine:
    """Class for storing CAN frame."""
    message_number: int
    time: float
    time_offset: float
    transmit: str
    identifier: int
    dlc: int
    data: str
    def __repr__(self):
        return f"Virtual {__class__}"

#Added benefit is __repr__() which allows to easily convert to body of trc file    
@dataclass
class TrcCanLine(CanLine):
    def __repr__(self):
        rep = ''
        SEPARATOR = '  '
        
        COUNTER_JUST =  7
        spaces = COUNTER_JUST - len(str(self.message_number))
        rep = ' '*spaces + str(self.message_number) + ')' + SEPARATOR
        
        TIME_JUST = 10
        time = '%.1f' % self.time_offset
        rep = rep + ' '*(TIME_JUST - len(time)) + time + SEPARATOR
        
        TX_JUST = 5
        rep = rep + self.transmit + ' '*(TX_JUST - len(self.transmit)) + SEPARATOR
        
        ID_JUST = 8
        hexid = '%08X' % self.identifier
        rep = rep + ' '*(ID_JUST - len(hexid)) + hexid + SEPARATOR
        
        rep = rep + str(self.dlc) + SEPARATOR
        
        rep = rep + self.data

        return rep

#Added benefit is __repr__() which allows to easily convert to body of asc file    
@dataclass
class AscCanLine(CanLine):
    def __repr__(self):
        rep = ''
        SEPARATOR = '  '
        
        TIME_JUST = 11
        time = '%08f' % (self.time_offset / 1000)
        rep = rep +' '*(TIME_JUST - len(time)) + time + ' 1'
        
        hexid = '%08X' % self.identifier
        rep = rep + SEPARATOR + hexid + 'x'
        
        rep = rep + ' '*7 + self.transmit
        
        rep = rep + SEPARATOR + ' d ' + str(self.dlc) + ' ' + self.data.rstrip()
                
        return rep



def build_asc_header(UnixModTime):
    asc_header = "date "

    fulldatetime = datetime.datetime.strptime(time.ctime(UnixModTime), "%c")
    #date_str = fulldatetime.strftime("%a %b %d %X %Y") #%X time approx doesn't use am/pm
    date_str = fulldatetime.strftime("%a %b %d %I:%M:%S %p %Y")
    #print(date_str)

    asc_header = asc_header + date_str +'\n'
    asc_header = asc_header + """base hex  timestamps relative
internal events logged
Begin Triggerblock
"""
    return asc_header




def build_trc_header(UnixModTime):
    trc_header = ";$FILEVERSION=1.1\n"
    trc_header = trc_header + ";$STARTTIME="

    #SEE https://www.peak-system.com/produktcd/Pdf/English/PEAK_CAN_TRC_File_Format.pdf
    #$STARTTIME is the days since 12/30/1899 and the fractional portion of the day since midnight.
    #This is slightly incorrect since it is using the end time as the base time.
    #NOT CONCERNED
    fulldatetime = datetime.datetime.strptime(time.ctime(UnixModTime), "%c")
    l_date = fulldatetime.date()
    f_date = datetime.date(1899, 12, 30)
    delta = l_date - f_date
    #print(delta.days)

    ms = fulldatetime.time()
    seconds_per_day = 3600*24
    seconds_since_midnight = (fulldatetime - fulldatetime.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    fractional_day = seconds_since_midnight / seconds_per_day
    #print(fractional_day)

    #WRITE TIMESTAMP
    bunkepoch = delta.days + fractional_day
    trc_header = trc_header + str(bunkepoch) 

    #FINISH BOILERPLATE
    trc_header = trc_header + """;
;
;   Columns description:
;   ~~~~~~~~~~~~~~~~~~~~~
;   +-Message Number
;   |          +Time offset (ms)
;   |          |        +Type
;   |          |        |        +ID (hex)
;   |          |        |        |     +Data Length Code
;   |          |        |        |     |   +Data bytes (hex)
;   |          |        |        |     |   |
;---+---   ----+----  --+--  ----+---  +  -+ -- -- -- -- -- -- --
"""
    return trc_header


def write_asc(fName, asc_canlines):
    #Write the asc file
    oName = fName.split('.')[0] + '.asc'

    UnixModTime = os.path.getmtime(fName)
    with open(oName, "wt") as of:
        of.write(build_asc_header(UnixModTime))
        for i in asc_canlines:
            of.write(i.__repr__() + '\n')
        of.write('End Triggerblock\n')
    print(f"Wrote {os.path.getsize(oName)} bytes to {oName}")



def write_trc(fName, trc_canlines):
    #Write the trace file
    oName = fName.split('.')[0] + '.trc'

    UnixModTime = os.path.getmtime(fName)
    with open(oName, "wt") as of:
        of.write(build_trc_header(UnixModTime))
        for i in trc_canlines:
            of.write(i.__repr__() + '\n')
    print(f"Wrote {os.path.getsize(oName)} bytes to {oName}")




#TXT CAN PARSER
#This will need to be modified on most runs
#Depending on how CAN KING is configured will have to skip lines or convert from base 10
def parse_lines(lines):  
    #extremely inefficient; whatever.
    asc_canlines = []
    trc_canlines = []

    prevtime = None
    line_count = 1

    #CAN KING had 2 formatters so lines were duplicated.  Only grab odd lines.
    #for i in range(1, len(lines) - 1, 2):
    #    line = lines[i]

    for line in lines[1:-2]:
        splitline = line.split()
        
        timestamp = float(splitline[-2])
        
        if prevtime is not None:
            time_offset = (timestamp - prevtime) * 1000
        else:
            time_offset = 0.0
        prevtime = timestamp
        
        if splitline[-1] == 'R':
            transmit = 'Rx'
        else:
            transmit = 'Tx'
            
        dlc = int(splitline[3])
        
        data = ''
        if dlc > 0 and dlc < 0xFF:
            for i in range(4, 4+dlc):
                data = data + '%02X' % int(splitline[i]) + ' '
        
        asc_canlines.append(AscCanLine(line_count, timestamp, time_offset, transmit, int(splitline[1]), dlc, data))
        trc_canlines.append(TrcCanLine(line_count, timestamp, time_offset, transmit, int(splitline[1]), dlc, data))
        line_count = line_count + 1
    return asc_canlines, trc_canlines



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify the .txt file to convert")
        sys.exit()
    else:
        fName = sys.argv[1]

    #UnixModTime = os.path.getmtime(fName)
    #print("Last modified: %s" % time.ctime(os.path.getmtime(fName)))

    with open(fName) as f:
        lines = f.readlines()
        print(f"Read {len(lines)} lines from file {fName}")
        #print(lines[0:2])

    asc_canlines, trc_canlines = parse_lines(lines)

    write_asc(fName, asc_canlines)
    write_trc(fName, trc_canlines)
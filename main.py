from machine import Pin, SoftI2C
import time
from struct import unpack

SCD41_I2C_ADDRESS = 0x62

i2c = SoftI2C(scl=Pin(33, pull=Pin.PULL_UP), sda=Pin(32, pull=Pin.PULL_UP))
print([hex(i) for i in i2c.scan()])

i2c.writeto(SCD41_I2C_ADDRESS, bytearray([0x00]))
print(f"SCD41 sensor found at {SCD41_I2C_ADDRESS:#x}")

def main():
    scd41_stop_periodic_measurement()
    time.sleep(1)
    scd41_start_periodic_measurement()
    print("SCD41: initialization finished")

    while True:
        if scd41_get_data_ready_status():
            raw_measurement = scd41_read_measurement()
            if scd41_is_data_crc_correct(raw_measurement):
                co2 = (raw_measurement[0] << 8) | raw_measurement[1]

                raw_temperature = (raw_measurement[3] << 8) | raw_measurement[4]
                temperature = round(-45 + 175 * (raw_temperature / (2 ** 16 - 1)), 1)

                raw_humidity = (raw_measurement[6] << 8) | raw_measurement[7]
                humidity = round(100 * (raw_humidity / (2 ** 16 - 1)), 1)

                print(f"CO2: {co2} ppm, Humidity: {humidity} %, Temperature: {temperature} °C")
        else:
            print("SCD41: no new data available")
        time.sleep(1)

def scd41_start_periodic_measurement():
    write_buffer = bytearray([0x21, 0xb1])
    i2c.writeto(SCD41_I2C_ADDRESS, write_buffer)

def scd41_stop_periodic_measurement():
    write_buffer = bytearray([0x3f, 0x86])
    i2c.writeto(SCD41_I2C_ADDRESS, write_buffer)

def scd41_get_data_ready_status():
    write_buffer = bytearray([0xe4, 0xb8])
    read_buffer = bytearray(3)
    i2c.writeto(SCD41_I2C_ADDRESS, write_buffer)
    time.sleep(0.001)
    i2c.readfrom_into(SCD41_I2C_ADDRESS, read_buffer, len(read_buffer))
    return (unpack(">H", read_buffer)[0] & 0x07ff)

def scd41_read_measurement():
    write_buffer = bytearray([0xec, 0x05])
    read_buffer = bytearray(9)
    i2c.writeto(SCD41_I2C_ADDRESS, write_buffer)
    time.sleep(0.001)
    i2c.readfrom_into(SCD41_I2C_ADDRESS, read_buffer, len(read_buffer))
    return read_buffer

def sensirion_common_generate_crc(buffer):
    crc = 0xff
    for byte in buffer:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
    return crc & 0xff

def scd41_is_data_crc_correct(buffer):
    crc_buffer = bytearray(2)
    for i in range(0, len(buffer), 3):
        crc_buffer[0] = buffer[i]
        crc_buffer[1] = buffer[i + 1]
        if sensirion_common_generate_crc(crc_buffer) != buffer[i + 2]:
            raise RuntimeError("CRC check failed while reading data")
    return True

main()

逐小时天气预报
平台: API 
逐小时天气预报API，提供全球城市未来24-168小时逐小时天气预报，包括：温度、天气状况、风力、风速、风向、相对湿度、大气压强、降水概率、露点温度、云量。

请求路径 
/v7/weather/{hours}
参数 
路径参数
hours(必选)预报小时数，支持最多168小时预报，可选值：
24h 24小时预报。
72h 72小时预报。
168h 168小时预报。
查询参数
location(必选)需要查询地区的LocationID或以英文逗号分隔的经度,纬度坐标（十进制，最多支持小数点后两位），LocationID可通过GeoAPI获取。例如 location=101010100 或 location=116.41,39.92
lang多语言设置，请阅读多语言文档，了解我们的多语言是如何工作、如何设置以及数据是否支持多语言。
unit数据单位设置，可选值包括unit=m（公制单位，默认）和unit=i（英制单位）。更多选项和说明参考度量衡单位。
请求示例 
curl -X GET --compressed \
-H 'Authorization: Bearer your_token' \
'https://your_api_host/v7/weather/24h?location=101010100'
请将your_token替换为你的JWT身份认证，将your_api_host替换为你的API Host

返回数据 
返回数据是JSON格式并进行了Gzip压缩。

{
  "code": "200",
  "updateTime": "2021-02-16T13:35+08:00",
  "fxLink": "http://hfx.link/2ax1",
  "hourly": [
    {
      "fxTime": "2021-02-16T15:00+08:00",
      "temp": "2",
      "icon": "100",
      "text": "晴",
      "wind360": "335",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "20",
      "humidity": "11",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-25"
    },
    {
      "fxTime": "2021-02-16T16:00+08:00",
      "temp": "1",
      "icon": "100",
      "text": "晴",
      "wind360": "339",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "24",
      "humidity": "11",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-16T17:00+08:00",
      "temp": "0",
      "icon": "100",
      "text": "晴",
      "wind360": "341",
      "windDir": "西北风",
      "windScale": "4-5",
      "windSpeed": "25",
      "humidity": "11",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1026",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-16T18:00+08:00",
      "temp": "0",
      "icon": "150",
      "text": "晴",
      "wind360": "344",
      "windDir": "西北风",
      "windScale": "4-5",
      "windSpeed": "25",
      "humidity": "12",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-16T19:00+08:00",
      "temp": "-2",
      "icon": "150",
      "text": "晴",
      "wind360": "349",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "24",
      "humidity": "13",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-16T20:00+08:00",
      "temp": "-3",
      "icon": "150",
      "text": "晴",
      "wind360": "353",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "22",
      "humidity": "14",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-16T21:00+08:00",
      "temp": "-3",
      "icon": "150",
      "text": "晴",
      "wind360": "355",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "20",
      "humidity": "14",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1026",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-16T22:00+08:00",
      "temp": "-4",
      "icon": "150",
      "text": "晴",
      "wind360": "356",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "18",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1026",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-16T23:00+08:00",
      "temp": "-4",
      "icon": "150",
      "text": "晴",
      "wind360": "356",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "18",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1026",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T00:00+08:00",
      "temp": "-4",
      "icon": "150",
      "text": "晴",
      "wind360": "354",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1027",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T01:00+08:00",
      "temp": "-4",
      "icon": "150",
      "text": "晴",
      "wind360": "351",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1028",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T02:00+08:00",
      "temp": "-4",
      "icon": "150",
      "text": "晴",
      "wind360": "350",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1028",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T03:00+08:00",
      "temp": "-5",
      "icon": "150",
      "text": "晴",
      "wind360": "350",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1028",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T04:00+08:00",
      "temp": "-5",
      "icon": "150",
      "text": "晴",
      "wind360": "351",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "15",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1027",
      "cloud": "0",
      "dew": "-28"
    },
    {
      "fxTime": "2021-02-17T05:00+08:00",
      "temp": "-5",
      "icon": "150",
      "text": "晴",
      "wind360": "352",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "14",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1026",
      "cloud": "0",
      "dew": "-29"
    },
    {
      "fxTime": "2021-02-17T06:00+08:00",
      "temp": "-5",
      "icon": "150",
      "text": "晴",
      "wind360": "355",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "16",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "0",
      "dew": "-27"
    },
    {
      "fxTime": "2021-02-17T07:00+08:00",
      "temp": "-7",
      "icon": "150",
      "text": "晴",
      "wind360": "359",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "20",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1024",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-17T08:00+08:00",
      "temp": "-5",
      "icon": "100",
      "text": "晴",
      "wind360": "1",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "19",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1023",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-17T09:00+08:00",
      "temp": "-4",
      "icon": "100",
      "text": "晴",
      "wind360": "356",
      "windDir": "北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "17",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1023",
      "cloud": "0",
      "dew": "-25"
    },
    {
      "fxTime": "2021-02-17T10:00+08:00",
      "temp": "-1",
      "icon": "100",
      "text": "晴",
      "wind360": "344",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "14",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1024",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-17T11:00+08:00",
      "temp": "0",
      "icon": "100",
      "text": "晴",
      "wind360": "333",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "12",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1024",
      "cloud": "0",
      "dew": "-26"
    },
    {
      "fxTime": "2021-02-17T12:00+08:00",
      "temp": "1",
      "icon": "100",
      "text": "晴",
      "wind360": "325",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "14",
      "humidity": "10",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "16",
      "dew": "-28"
    },
    {
      "fxTime": "2021-02-17T13:00+08:00",
      "temp": "2",
      "icon": "100",
      "text": "晴",
      "wind360": "319",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "8",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "32",
      "dew": "-29"
    },
    {
      "fxTime": "2021-02-17T14:00+08:00",
      "temp": "2",
      "icon": "100",
      "text": "晴",
      "wind360": "313",
      "windDir": "西北风",
      "windScale": "3-4",
      "windSpeed": "16",
      "humidity": "9",
      "pop": "0",
      "precip": "0.0",
      "pressure": "1025",
      "cloud": "48",
      "dew": "-27"
    }
  ],
  "refer": {
    "sources": [
      "QWeather",
      "NMC",
      "ECMWF"
    ],
    "license": [
      "QWeather Developers License"
    ]
  }
}
code 请参考状态码
updateTime 当前API的最近更新时间
fxLink 当前数据的响应式页面，便于嵌入网站或应用
hourly.fxTime 预报时间
hourly.temp 温度，默认单位：摄氏度
hourly.icon 天气状况的图标代码，另请参考天气图标项目
hourly.text 天气状况的文字描述，包括阴晴雨雪等天气状态的描述
hourly.wind360 风向360角度
hourly.windDir 风向
hourly.windScale 风力等级
hourly.windSpeed 风速，公里/小时
hourly.humidity 相对湿度，百分比数值
hourly.precip 当前小时累计降水量，默认单位：毫米
hourly.pop 逐小时预报降水概率，百分比数值，可能为空
hourly.pressure 大气压强，默认单位：百帕
hourly.cloud 云量，百分比数值。可能为空
hourly.dew 露点温度。可能为空
refer.sources 原始数据来源，或数据源说明，可能为空
refer.license 数据许可或版权声明，可能为空



我的：
API Host：
nh6r6wdwq5.re.qweatherapi.com

API KEY
2d02df07249c49a190b28d7316ec8f0f
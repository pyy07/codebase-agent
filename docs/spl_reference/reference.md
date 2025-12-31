# SPL 搜索参考文档

> 文档来源: http://log.gf.com.cn/docs/search_reference/
> 下载时间: 2025-12-29 11:13:57
> 获取方式: 浏览器自动化（Playwright）

---

# 日志易检索参考
北京优特捷信息技术有限公司
version 4.1,
2021-11-09
Table of Contents
- 1. 搜索命令简要描述
- 2. 搜索命令类型2.1. 按照执行阶段分类2.1.1. 集中式命令2.1.2. 分布式命令2.1.3. 命令类型列表2.2. 按照功能分类2.2.1. 生成命令2.2.2. 流式命令2.2.3. 转换命令2.2.4. 命令类型列表
- 3. 搜索命令函数3.1. 搜索命令函数参数说明补充3.1.1. printf函数的format参数类型3.1.2. tonumber的参数类型3.1.3. in函数
- 4. 与stats有关的函数
- 5. 常见的时间和时间格式5.1. 时间格式5.2. 与搜索结合使用的时间修饰符
- 6. 检索指令6.1. search6.2. multisearch6.3. addinfo6.4. append6.5. union6.6. appendcols6.7. autoregress6.8. bucket6.9. composite6.10. chart6.11. collect6.12. correlation6.13. dbxexec6.14. dbxlookup6.15. dbxoutput6.16. dbxquery6.17. dedup6.18. delete6.19. download6.20. esma6.21. eval6.22. eventstats6.23. fields6.24. filldown6.25. fillnull6.26. foreach6.27. fromes6.28. fromkafkapy6.29. gentimes6.30. geostats6.31. inputlookup6.32. iplocation6.33. join6.34. jpath6.35. kvextract6.36. ldapfetch6.37. ldapfilter6.38. ldapgroup6.39. ldapsearch6.40. ldaptestconnection6.41. limit6.42. head6.43. lookup6.44. lookup26.45. makecontinuous6.46. makeresults6.47. map6.48. movingavg6.49. mvcombine6.50. mvexpand6.51. outputlookup6.52. parse6.53. partition6.54. rare6.55. rename6.56. rollingstd6.57. save6.58. sort6.59. stats6.60. streamstats6.61. table6.62. timechart6.63. timewrap6.64. top6.65. transaction6.66. transpose6.67. unpivot6.68. where6.69. xpath6.70. replace6.71. makemv6.72. localop6.73. strcat6.74. loadjob6.75. accum6.76. untable6.77. rest6.78. typeahead6.79. history6.80. addcoltotals6.81. addtotals6.82. multireport
- 7. SPL中使用注释
- 8. Logtail功能
- 9. Download功能
- 10. 搜索宏功能
- 11. 高基功能(Flink)
- 12. 自定义命令功能12.1. 摘要：12.1.1. 自定义命令执行文件示例：
## 1. 搜索命令简要描述
| 命令 | 描述 | 示例 |
| --- | --- | --- |
| search | 指定的搜索条件，或者作为过滤条件 | host: localhost AND status: >=200 |
| multisearch | 同时执行多个搜索，子查询只允许分布式流式命令 | …​ | multisearch [[ status: 200 | eval tag=succ ]] [[ status: 404 | eval tag=err ]] |
| addinfo | 向每个事件添加包含有关搜索的全局通用信息的字段 | …​ | addinfo |
| append | 将子管道的结果附加在主管道的结果之后 | …​ | append [[ * | stats max(status) by appname ]] |
| union | 同时执行多个搜索，子查询可以用任意命令 | …​ | union [[ * | stats max(status) by appname ]] [[ * | stats max(status) by tag ]] |
| appendcols | 添加一个子搜索，并将子搜索的结果按顺序合并到父搜索上 | …​ | appendcols [[ * | stats min(timestamp)]] |
| autoregress | 拷贝一个或者多个当前事件之前的事件中的字段值到当前事件 | …​ | autoregress clientip p=1-2 |
| chart | 按照over字段进行分桶后的统计行为 | …​ | chart sep="," format="$VAL**$AGG" limit=5 cont=false rendertype="pie" count(apache.x_forward) over apache.status |
| collect | 将查询的结果写到索引 | …​ |collect index=test marker="appname=\"test\", tag=\"tag1\"" |
| bucket | 将连续的值放入离散集中 | …​ | bucket timestamp span=1h as ts |
| dedup | 对搜索结果中指定字段值的重复情况进行去重和过滤 | …​ | dedup 3 apache.status, apache.geo.city |
| dbxlookup | 类似sql的连接，将来自远程数据库表的结果和子管道的结果连接在一起 | | dbxlookup lookup="test1"| dbxlookup test1,test2 connection="179test" query="select * from test" on id=bid |
| dbxoutput | 将当前搜索的数据按照已配置的dbxoutput名称写出到远程数据库。 | | dbxoutput output="test1" |
| dbxquery | 是一个可以使用sql来查远程数据库的数据并作为spl的查询语句的命令 | | dbxquery connection="179test" query="select * from test" |
| esma | 对某一个字段的未来值进行预测 | …​ | esma latency timefield=ts period=7 futurecount=30 |
| eval | 计算表达式，并将表达式的值放入字段中，请参阅 搜索命令函数 | …​ | eval username = case(user_name, user) |
| eventstats | 提供统计信息，可以选择字段进行分组，并且将按照当前行所属于的分组的统计结果作为新的字段值添加在本行 | …​ | eventstats count() by logtype |
| fields | 通过操作符保留或排除结果中的系列字段 | …​ | fields status, clientip |
| filldown | 将某些字段的null值用之前最近的非null值进行填充，支持通配符 | …​ | filldown hostname app* |
| fillnull | 将空值替换为指定值 | …​ | fillnull value="aaa" foo,bar |
| gentimes | 可以生成指定时间范围内的时间戳 | | gentimes start="2019-01-01:00:00:00" end="2019-01-04:00:00:00" |
| geostats | 可以基于地理位置信息，即经度和纬度进行分区域统计 | …​ | geostats count(appname) |
| inputlookup | 可以读取csv文件 | | inputlookup a.csv |
| join | 类似sql的连接，将来自主管道的结果和子管道的结果连接在一起 | …​ | join type=left clientip [[ * | stats avg(resp_len) by clientip ]] |
| jpath | 类似xpath抽取json中的字段值 | …​ | jpath output=prices path="store.book[*].price" |
| kvextract | 将指定字段按键值对抽取 | …​ | kvextract json.kvex |
| limit | 返回前n个结果 | …​ | limit 10 |
| lookup | 显示调用字段值查找 | …​ | lookup emailhttp://data.cn/user.csv onid=userId |
| lookup2 | 显示调用指定方式查找 | …​ | lookup2 external_file outputfields appname,hostname |
| makecontinuous | 在一定数值或时间范围内，根据给定的区间大小，对原始数据升序处理，并补充不连续的区间，区间的划分采用向前圆整的方式 | …​ | makecontinuous time span=3 start=216 end=226 |
| makeresults | 构造指定的结果 | | makeresults count=1 |
| map | 将前一个查询的结果用于下一个查询 | …​ | map "apache.status:$apache.status$ | stats count()" |
| movingavg | 计算移动平均值 | …​ | movingavg sum_len,10 as smooth_sum_len |
| mvexpand | 拆分多值字段 | …​ | mvexpand iplist limit=100 |
| mvcombine | 合并指定字段 | …​ | mvcombine sep="," ip |
| nomv | 将多值字段转换为单值字段 | …​ | nomv delim="," a |
| outputlookup | 导出csv文件 | …​ | outputlookup createempty=false overrideifempty=false maxresult=100 filename.csv |
| parse | 搜索时抽取字段 | …​ | parse "(?<ip_addr>\d+\.\d+\.\d+\.\d+)" |
| rename | 重新命名指定字段 | …​ | rename apache.status as http_code |
| rollingstd | 计算移动的标准差 | …​ | rollingstd sum_resp_len, 10 as resp_len_rolling_std |
| save | 将搜索结果输出为外部文件 | …​ | save /data/spldata/apahce_clientip.csv |
| sort | 按照指定的字段对结果进行排序 | …​ | sort by apache.status |
| stats | 提供统计信息，可以选择按照字段分组 | …​ | stats count() by apache.method |
| streamstats | 连续统计 | …​ | streamstats count() as cnt |
| table | 将查询结果以表格形式展示，并对字段进行筛选 | …​ | table apache.status, apache.method |
| timechart | 对时间分桶进行统计查询 | …​ | timechart limit=5 bins=10 minspan=1m span=10m max(x) as ma count() as cnt by apache.geo.city |
| timewrap | 对timechart命令的结果进行显示或者折叠 | …​ | top 3 apache.clientip by apache.method |
| top | 返回指定字段top的值集合 | …​ | top 3 apache.clientip by apache.method |
| rare | 返回指定字段最少出现次数的值集合 | …​ | rare apache.clientip by apache.method |
| transaction | 将结果分组成交易 | …​ | transaction apache.clientip startswith="Android 4.3" endswith="AndroidPhone" maxopenevents = 10 |
| transpose | 将查询的表格结果进行行列转换 | …​ | transpose row=apache.method column=apache.status valuefield=cnt |
| where | 使用表达式对结果进行过滤 | …​ | where apache.status < 200 && apache.status>400 |
| xpath | 提供对xml数据的处理和抽取 | …​ | xpath input=json.xp output=lyly path="/purchases/book/title" |
| unpivot | 行转列转换 | …​ | unpivot 10 header_field=count column_name=title |
| foreach | 对字段列表执行流式命令 | …​ | foreach count* [[ eval <<FIELD>> = <<FIELD>> + 1 ]] |
| iplocation | 从ip地址抽取地理信息 | …​ | iplocation clientip |
| replace | 使用指定字符串替换字段值，可以指定一个或多个字段，仅替换指定字段的值，如果没有指定字段，则替换所有字段 | …​ | replace "192.168.1.1" with "localhost" |
| makemv | 使用分隔符或者带捕获组的正则表达式，将单值字段转换为多值字段 | …​ | makemv delim="," testmv |
| localop | localop命令强制随后的命令都在spl单机执行 | …​ | localop |
| strcat | 连接来自2个或更多字段的值。将字段值和指定字符串组合到一个新字段中 | …​ | eval field1=\"10.192.1.1\",field2=\"192.168.1.1\" |strcat field1 \"abcd\" field2 |
| loadjob | 加载先前完成的定时任务或告警的执行结果。由ID 和type唯一确定一个任务。如果最近一次时间点的结果不存在，则临时运行原始查询。 | …​ | loadjob id=1,type="savedschedule" |
| accum | 对每个事件中为数字的指定字段进行逐次累加，得到的累加结果会放入该字段或者新字段中。 | …​ | accum apache.resp_len as sum_resp_len |
| untable | table指令的逆操作，使用该指令可以将表格的查看方式转换到事件列表的查看方式。 | …​ | untable |
| rest | 调用日志易API，返回对应结果 | …​ | rest /agentgroup/ apikey="user apikey" count=2 |
| typeahead | 返回指定前缀的字段信息。返回的最大结果数取决于为size参数指定的值。typeahead命令可以以指定索引为目标，并受时间限制。 | …​ | typeahead prefix="app" size=5 index=yotta |
| history | 查看搜索历史记录 | …​ | history |
| correlation | 计算的与搜索结果相关性高的字段与字段值 | …​ | bucket timestamp ranges=0, 1000),(1000, 10000),(1000, 1753587702986 as ts| correlation bucket_field=ts|sort by correlation| sort by -ts |
| fromes | 搜索指定索引的数据 | |fromes host=10.200.0.140 index=logs-my_app-default querydsl='{"query": {"match_all": { }}}' |
| fromkafkapy | 消费指定主题的数据 | |fromkafkapy topic=test |
| addcoltotals | 在搜索结果集中添加汇总行 | …​ | addcoltotals |
| addtotals | 默认在搜索结果集中添加汇总列且列名为Total；同时可以在搜索结果中添加汇总行，可指定列名和行名，可指定求和行/列 | …​ | addtotals col=true labelfield=products label="Quarterly Totals" fieldname="Product Totals" |
| multireport | 对同一数据流做不同的处理，最后汇聚输出 | …​ | multireport [[ |
| where _c%2==0 | eval v=0]] [[ | where _c%2==1 |
## 2. 搜索命令类型
### 2.1. 按照执行阶段分类
命令的处理流程：当SPL模块接收到SPL搜索语句时，找到第一个出现的集中式命令，将之前的分布式命令下沉到引擎分布式处理，后半部分交由SPL集中式处理。
#### 2.1.1. 集中式命令
集中式命令
**只能**
在SPL单机执行。
#### 2.1.2. 分布式命令
分布式命令可以在引擎分布式执行，也可以在spl集中式执行。分布式命令使用了多机资源，性能更好。
分布式命令在不同位置执行模式有所不同，最终是否是分布式执行，由下面的规则决定：
- 如果一个命令可分布式，并且之前的命令都是分布式执行的，那这个命令是分布式执行；
- 如果一个命令是集中式执行的，之后的命令都是集中式执行；
- query查询部分不能在spl执行，只能在引擎执行。
例如
`* | eval …​ | parse …​`
中的eval，parse都是分布式执行。
例如
`* | transaction …​| eval …​ | parse …​`
中的transaction是集中式命令，所以eval，parse都是集中式执行。
#### 2.1.3. 命令类型列表
| 集中式命令 | 分布式命令命令 |
| --- | --- |
| sort | append |
| appendcols | autoregress |
| collect | custom command |
| dbxlookup | ldaptestconnection |
| dbxoutput | lookup |
| dbxquery | lookup2 |
| dedup | limit |
| delete | makecontinuous |
| download | makeresults |
| esma | map |
| eventstats | movingavg |
| filldown | mvcombine |
| gentimes | mvexpand |
| inputlookup | outputlookup |
| join | rollingstd |
| ldapfetch | save |
| ldapfilter | streamstats |
| ldapgroup | table |
| ldapsearch | timewrap |
| transaction | transpose |
| unpivot | loadjob |
| localop | accum |
| untable | rest |
| fromes | addcoltotals |
| fromkafkapy |  |
| correlation |  |
|  |  |
### 2.2. 按照功能分类
SPL的搜索命令类型有下面几种
- 生成命令
- 流式命令
- 转换命令
#### 2.2.1. 生成命令
生成数据的命令，用于产生数据，通常是命令或者子命令的第一个命令。
#### 2.2.2. 流式命令
流式命令对数据一行一行处理，处理一行产生一行结果。
分布式流式命令是可以分布式执行的流式命令，对数据一行一行处理，处理一行产生一行结果，不依赖全局顺序和上下行的命令，比如eval，parse。
集中式流式命令，也对数据一行一行处理，和分布式流式命令区别在，依赖输入数据的顺序，比如autoregress，filldown。
还有一些集中式流式命令是暂时只在SPL实现的，不在引擎执行的命令，具体参考命令类型列表。
#### 2.2.3. 转换命令
把输入命令作为一个整体来处理， 需要所有数据才能产生结果，比如transpose，dedup。这类命令在SPL执行，不可分布式执行。
#### 2.2.4. 命令类型列表
以下是搜索命令的类型，支持分布式命令有特殊说明，否则是集中式的。
| 生成命令 | 流式命令 | 转换命令 |
| --- | --- | --- |
| search | addinfo | chart |
| multisearch | append | dbxoutput |
| union | appendcols | dedup |
| gentimes | bucket | esma |
| inputlookup | collect | eventstats |
| makeresults | dbxlookup | geostats |
| dbxquery | eval | makecontinuous |
| history | fields | map |
| loadjob | filldown | mvcombine |
| rest | fillnull | outputlookup |
| typeahead | foreach | rare |
| fromes | head | save |
| fromkafkapy | iplocation | sort |
|  | join | stats |
|  | jpath | timechart |
|  | kvextract | timewrap |
|  | limit | top |
|  | lookup | transpose |
|  | lookup2 | unpivot |
|  | movingavg | correlation |
|  | mvexpand |  |
|  | nomv |  |
|  | parse |  |
|  | rename |  |
|  | replace |  |
|  | rollingstd |  |
|  | streamstats |  |
|  | table |  |
|  | transaction |  |
|  | where |  |
|  | xpath |  |
|  | makemv |  |
|  | localop |  |
|  | strcat |  |
|  | accum |  |
|  | untable |  |
| addcoltotals |  |  |
## 3. 搜索命令函数
| 函数 | 描述 | 示例 |
| --- | --- | --- |
| abs(X) | 此函数获取一个数字X，并返回其绝对值 | 以下示例返回absv，该变量的值为数值字段value的绝对值：…​ | eval absv = abs(value) |
| exp(X) | 此函数获取一个数字X，并返回e的X次方 | 以下示例返回y，该变量的值为e的3次方：…​ | eval y = exp(3) |
| ln(X) | 此函数获取一个数字X，并返回X的自然对数（以e为底） | 以下示例返回y，该变量的值为bytes的自然对数：…​ | eval lnBytes = ln(bytes) |
| empty(x) | 判断某个field是否为空。也可写作isempty(X) | empty(field)如果存在返回false，否则返回true。也可写作isempty(field)比如：empty(apache.status) |
| case(X, "Y", …​， [default, Z]) | 此函数会获取X, Y的参数对，X参数必须为布尔表达式，如果结果为true，则返回响应的Y的值，如果计算结果均为false, 则返回default对应的值，default部分为可选，不指定default，则default的返回为空值 | 以下示例返回http状态代码的描述…​ | eval desc = case(error == 200, "OK", error == 500, "Internal Server Error ", default, "Unexpected error") |
| ceil(X) | 函数返回X向上取整的整数值 | 以下示例返回n = 5…​ | eval n = ceil(4.1) |
| cidrmatch(X, Y) | 字段X必须是无分类和子网地址扩展(CIDR)，字段Y为一个IP地址，判断IP地址Y的子网地址是否和X匹配 | 示例：…​| eval matched = cidrmatch("192.168.1.130/25", "192.168.1.129")'将192.168.1.130转换为二进制并保留高位的25位，低位设为0得到下限（不包括），对应的ip为192.168.1.128将192.168.1.130转换为二进制保留高位的25位，低位全部设置为1得到上限（不包括），对应的ip地址为192.168.1.255因此ip的范围是(192.168.1.128, 192.168.1.255)凡落在此范围的ip地址均match成功，因此matched的值为true |
| coalesce(X, …​) | 此函数接受任意数量的并返回第一个不为空值的值，如果所有参数都是空值，则返回空值 | 假设有一部分日志，用户名字段放在user_name或者user字段里，以下示例定义名为username的字段，该字段值为user_name和user字段不是空值的那一个：…​ | eval username = coalesce(user_name, user) |
| floor(X) | 函数向下取整为最接近的整数 | 以下示例返回 n = 4…​ | eval n = floor(4.1) |
| format(FORMAT, [X…​]) | 格式化字符串, 提供类似printf的功能FORMAT，为printf函数的format字符串 | 示例：format("%.1fMB", rate)输出速率，rate保留小数点后一位format("%s ⇒ %s", "aa", "bb")输入"aa ⇒ bb"NOTE: 变量类型和format中%x需要对应正确，否则可能导致计算失败，而输出空值 |
| formatdate(X[, Y]) | 该函数对X对应UTC时间值格式化为Y具体的时间格式Y的时间格式字符串遵循java.text.SimpleDateFormat支持的格式，如果不指定Y，则默认的时间格式为"yyyy-MM-dd HH:mm:ss.SSS"，暂不支持时区的自定义 | 以下示例将返回timestamp所表示的时间的小时和分钟…​ | eval v = formatdate(timestamp, "HH:mm") |
| datetime_diff(X, Y[, Z]) | 该函数接受两个时间戳，返回两个时间戳之间的时间差，单位为毫秒。可以指定返回的时间单位，d=天,h=小时,m=分钟,s=秒,默认为ms | 以下示例将返回1655870082000-1655870081000的时间差，单位为毫秒…​ | eval v = datetime_diff(1655870081000, 1655870082000) |
| if(X, Y, Z) | 函数接受3个参数，第一个X为布尔表达式，如果X的计算结果为true，则结果为第二个参数Y的值，否则返回第三个参数Z值 | 以下示例将检查status的值，如果status==200，则返回”OK”，否则返回Error…​ | eval desc = if (status == 200, "OK", "Error") |
| in(field, X, …​) | 给定一个字段和若干指定值，判断字段中的值是否在指定值中存在。存在返回true，不存在返回false | 示例：…​ | eval field = 'appname' | where in(field, 'appname', 'hostname') |
| isnum(X) | 判断字段X是否为数值类型，对于整数类型或者浮点型结果都会返回true，其它返回false | 示例：…​ | eval a = isnum(apache.status) |
| isstr(X) | 判断字段X是否为字符串类型 | 示例:…​| eval a = isstr(apache.method) |
| len(X) | 函数接收一个字符串类型的参数，返回字符串的长度 | 如果method的字段值为GET，以下示例n的值为3…​ | eval n = len(method) |
| log(X [,Y]) | 此函数接受一个或两个数值类型的值，返回以Y为底X的对数，Y默认为10 | 以下示例将返回以2为底，number的对数…​ | eval num=log(number,2) |
| pi() | 此函数返回pi的值 | 以下示例将返回圆的面积…​ | eval area_circle=pi()*pow(radius,2) |
| pow(X, Y) | 此函数接受两个数值类型的参数，返回X的Y次方 | 假设number的值为2，以下示例将返回8…​ | eval n=pow(number,3) |
| sqrt(X) | 此函数接受一个数值类型的参数，返回X的平方根 | 假设number的值为4，以下示例将返回2…​ | eval n=sqrt(number) |
| acos(X) | 此函数接受一个范围在(-1,1)之间的数值类型的参数，返回以弧度表示的X的反余弦值 | 以下示例返回0的反余弦值…​ | eval result = acos(0) |
| acosh(X) | 此函数接受一个大于等于1的数值类型的参数，返回以弧度表示的X的反双曲余弦值 | 以下示例返回1的反双曲余弦值…​ | eval result = acosh(1) |
| asin(X) | 此函数接受一个范围在[-1,1]之间的数值类型的参数，返回以弧度表示的X的反正弦值 | 以下示例返回0的反正弦值…​ | eval result = asin(0) |
| asinh(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的反双曲正弦值 | 以下示例返回5的反双曲正弦值…​ | eval result = asinh(5) |
| atan(X) | 此函数接受一个范围在 [-pi/2,+pi/2] 之间的数值类型的参数，返回以弧度表示的X的反正切值 | 以下示例返回0.5的反正切值…​ | eval result = atan(0.5) |
| atan2(Y, X) | 此函数接受两个数值类型的参数，返回以弧度表示的 Y/X 的反正切值，X的取值范围在 [-pi,+pi]之间 | 以下示例返回0.5，0.75的反正切值…​ | eval result = atan2(0.5, 0.75) |
| atanh(X) | 此函数接受一个范围为(-1,1)之间的数值类型的参数，返回以弧度表示的X的反双曲正切值 | 以下示例返回0.5的反双曲正切值…​ | eval result = atanh(0.5) |
| cos(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的余弦值 | 以下示例返回0的余弦值…​ | eval result = cos(0) |
| cosh(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的双曲余弦值 | 以下示例返回0的双曲余弦值…​ | eval result = cosh(0) |
| hypot(X, Y) | 此函数接受两个数值类型的参数，返回欧几里得范数，即sqrt(X^2 + Y^2) | 以下示例返回2，2的欧几里得范数…​ | eval result = hypot(2,2) |
| sin(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的正弦值 | 以下示例返回0的正弦值…​ | eval result = sin(0) |
| sinh(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的双曲正弦值 | 以下示例返回0的双曲正弦值…​ | eval result = sinh(0) |
| tan(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的正切值 | 以下示例返回0的正切值…​ | eval result = tan(0) |
| tanh(X) | 此函数接受一个数值类型的参数，返回以弧度表示的X的双曲正切值 | 以下示例返回0的双曲正切值…​ | eval result = tanh(0) |
| entropy(field) | 此函数计算指定字段的熵值 | 以下示例返回json.name的熵值…​ | eval e = entropy(json.name) |
| lower(X) | 此函数接受一个字符串类型的参数，返回其小写形式 | 假设method的值为GET，以下示例将返回”get”…​ | eval lowerstr = lower(method) |
| match(X, Y) | 此函数将使用正则表达式Y对X进行匹配，返回是否匹配成功 | 当且仅当字段于IP地址的基本形式匹配时，则返回true，否则返回false，这里使用了^和$表示执行完全匹配…​ | eval matched = match(ip, "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$") |
| contains(X,Y) | 此函数会判断字符串X的值与字符串Y进行匹配，返回是否匹配成功,Y可以是多值字符串，Y是多值的情况下，包含Y中的任意一个则返回true，否则返回false | 以下实例将返回 true …​|eval a = split("a,b,c,e",",")|eval b = "Hello,world!" |eval c = contains(b,a) |
| max(X,…​) | 此函数接受至少一个数值类型的参数，返回值较大的那个值 | 以下示例将返回101…​ | eval maxv = max(101, 100.0) |
| min(X,…​) | 此函数接受至少一个数值类型的参数，返回较小的那个值 | 以下示例将返回 100.0…​ | eval minv = min(101, 100.0) |
| mvsum(X,…​) | 此函数接受至少一个数值类型的多值字段或单值字段做为参数，返回所有参数的总和 | 以下示例将返回多值字段multiv的值与2的总和…​ | eval v = mvsum(multiv, 2) |
| mvavg(X,…​) | 此函数接受至少一个数值类型的多值字段或单值字段做为参数，返回所有参数的平均值 | 以下示例将返回多值字段multiv的值与2的平均值,多值字段的每个值都会使计算平均值的分母加1…​ | eval v = mvavg(multiv, 2) |
| mvappend(X,…​) | 该函数为任意个参数，参数可以为字符串，多值字段，或者单值字段等 | …​ | eval v=mvappend(initv, "middle") |
| mvcount(X) | 该函数只有一个参数X，如果X是多值字段，则返回多值字段的值个数，如果是单值字段，则返回1，其他返回0 | …​ | eval c=mvcount(mvfield) |
| mvdedup(X) | 该函数接收一个多值参数X，返回字段值消重后的多值类型 | …​ | eval v=mvdedup(mvfield) |
| mvfilter(X, filterexpr) | X为类型为多值的参数，filterexpr为过滤条件表达式，其中使用_x描述X中的单个值对mv多值字段进行过滤，仅保留1a的值 | mvfilter(mv, _x == "1a") |
| mvfind(X,V) | X为多值类型的参数，V表示需要查找的值，如果找到返回对应下表，否则返回-1 | …​ | eval n=mvfind(mymvfield, "err") |
| mvindex(X,start[, end]) | X为多值类型的参数，如果无end参数，则返回下表为start的元素，如果start不合法则返回null，否则返回从下标start到下标end（不包括）元素组成列表，如果下表范围不合法返回空数组，NOTE: 数组下表从0开始 | …​ | eval v = mvindex(mv, 10, -1) |
| mvjoin(X,DELIMITER) | 将多值字段X的值使用分隔符DELEMITER组成一个字符串 | eval v = mvjoin(mv, ", ") |
| mvmap(X,mapexpr) | X为多值类型，mapexpr为转换的表达式，使用_x表示X中的单个值，返回的多值类型为X中的每个元素使用mapexpr转换得到的值组成的多值类型 | …​ | eval x = mvmap(X, tolong(_x) + 2)设X = ["1", "3", "4"]则x = [3, 5, 6] |
| mvdelta(X) | X为多值类型，该函数按顺序计算当前的值与前一个值的差,写入一个新的多值字段中，返回新的多值字段 | …​ | eval x = mvdelta(X)设X = ["1", "3", "4"]则x = [2, 1] |
| mvrange(X,Y[,Z]) | 该函数使用一个数值的区间生成一个多值字段，其中X表示区间起始值，Y表示区间结束值（不包括），Z表示步跳数，默认为1 | 下例返回 1, 3, 5, 7.…​ | eval mv=mvrange(1,8,2) |
| mvsort(X) | 对多值字段进行排序 | …​ | eval s=mvsort(mv) |
| mvszip(X,Y[,"Z"]) | X和Y都为多值类型，将X中的第一个元素和Y中的第一个元素都转换为字符串，并以Z为分隔符进行拼接，得到返回结果多值结果的第一个元素，类型为字符串，然后按照同样方法对X的第二个元素和Y中的第二个元素进行拼接，以此类推得到一个多值的结果。如果X和Y的长度不等，则当X或者Y处理完最后一个元素后不再进行拼接。 | X = [1, 3, 4, 7]Y = [2, 5, 8]mvszip(X, Y) = ["1,2", "3,5", "4,8"] |
| split(S, SEP) | X为字符串类型，使用字符串SEP分割符对S进行拆分成多值类型，如果SEP为空字符串，则S将被拆分为单字组成的多值类型 | 如X = ":abc::edf: "则split(X, ":") = ["", "abc", "", "edf", " "] |
| now() | 函数用于表示当前时间，实际值为搜索请求收到的时间，在一个请求中多次调用返回的是同一个值，值为1970-01-01:00:00:00到当前时间的毫秒数，类型为long | 示例:…​|eval current_time = now() |
| parsedate(X, Y[, Z]) | 解析日期时间串为unix时间戳X为日期的字符串，Y为日期的格式说明，遵循java.text.SimpleDateFormat支持的时间格式，Z为可选参数，指定Locale，默认为en（english） | 示例：parsedate("Thu 28/04/2016:12:01:01""EEE dd/MM/yyyy:HH:mm:ss")其中EEE或者E表示星期几;parsedate("28/四月/2016", "dd/MMM/yyyy", "zh")其中zh表示中文的Locale;parsedate("2017-January-01", "yyyy-MMMM-dd", "UTC", "en")其中UTC代表时区，en表示英文的Locale |
| printf(FORMAT, [X…​]) | 格式化字符串(格式) | 示例: printf("%.1fMB", rate)输出速率，rate保留小数点后一位printf(“%s ⇒ %s", "aa", "bb")输入"aa ⇒ bb"NOTE: 变量类型和printf中%x需要对应正确，否则可能导致计算失败，⽽输出空值 |
| relative_time(X, Y) | 字段X必须是时间类型，字段Y必须为一个date math(请参考时间格式一节)的相对时间值，返回基于时间戳X的date math的计算结果 | 示例：…​ | eval ts = relative_time(timestamp, "-1d/d")返回得到timestamp所代表的时间减去1天的毫秒数，并圆整到0点，即timestamp表示的日期的前一天的零点。 |
| round(X [,Y]) | 把数值X近似到小数点后Y位;Y参数默认值为0，即近似为整数(round会把X近似为“最近的值”;当距离相同时，近似为更⼤的值) | 示例: round(3.14)输出3;round(3.1415,3)输出3.142;注:当round(-1.5)输出-1;round(1.5)输出2 |
| substring(X, Y[, Z]) | 此函数接收三个参数，其中X必须为字符串，Y和Z是数字（Y和Z从0开始），返回X的子字符串，返回X的第Y个字符到第Z个（不包括）字符之间的字符 ，如果不指定Z则返回Y位置开始的剩余字符串 | 以下示例返回"bce"…​ | eval subs = substring("abcedfg", 1, 4) |
| todouble(X) | 该函数接受一个参数，可以是字符串或者数值型，返回对应的双浮点数的值 | 以下示例返回123.1…​ | eval value = todouble("123.1") |
| tonumber | tonumber(numStr[, base]) | 将数字或字符串转化为数值类型，并可将2-36进制转换为10进制，base默认为10进制 |
| tolong(X) | 该函数接受一个参数，字符串或者数值类型，返回对应的long值，X为10进制 | 以下示例返回123…​ | eval value=tolong("123") |
| tostring(X) | 该函数接收一个参数，可以是字符串或者数值类型，返回对应的字符串的值 | 以下示例返回”123.1”…​ | eval strv = tostring(123.1) |
| tojson(X) | 该函数接收一个任意类型的参数，返回对应的 json 字符串 | 假设 a = [1,2,3],那么 "[1,2,3]" 是命令 …​|eval json_str = tojson(a)的结果 |
| trim(X) | 该函数接受一个字符串类型的参数，返回X前后去除空白符的字符串值 | 以下示例返回" bcd ef"…​ | eval strv = trim("  bcd ef   \t") |
| ltrim(X[, Y]) | 该函数接受一个字符串类型的参数，返回X去除左边空白符的字符串值。或者接收两个字符串类型的参数,用Y字符串从左侧去除在Y中出现过的字符,直到遇到第一个不在Y中的字符为止。 | 以下示例返回"yi"…​ | eval strv = ltrim("rizhiyi", "irhz") |
| rtrim(X[, Y]) | 该函数接受一个字符串类型的参数，返回X去除右边空白符的字符串值。或者接收两个字符串类型的参数,用Y字符串从右侧去除在Y中出现过的字符,直到遇到第一个不在Y中的字符为止。 | 以下示例返回"rizhiy"…​ | eval strv = rtrim("rizhiyi", "irhz") |
| replace(<str>,<regex>,<replacement>) | 此函数用replacement字符串替换字符串str中每次出现的regex。 | 以下示例会将月份和日期数字调换位置。如果输入为 1/14/2020 ，则返回值为 14/1/2020。…​ | eval n=replace(date, "^(\d{1,2})/(\d{1,2})/", "\2/\1/") |
| typeof(X) | 获取字段X的类型支持类型为: long, double, int, float, short, string, object, array, bool如果字段为null，则返回null | 示例：…​ | eval a_type = typeof(apache.method) |
| upper(X) | 函数接收一个字符串类型的参数，返回X的大写形式 | 以下示例返回GET…​ | eval strv = upper("Get") |
| urlencode(X) | 对字段X的值执行URL编码，字段X必须为字符串NOTE: 目前还不支持指定字符编码 | 示例:…​ | eval url = urlencode(url) |
| urldecode(X) | 对字段X的值执行URL解码，字段X必须为字符串NOTE: 目前还不支持指定字符编码 | 示例:…​ | eval url = urldecode(url) |
| base64encode(X) | 对字段X的值执行base64编码，字段X必须为字符串 | 示例:…​ | eval base64 = base64encode(base64) |
| base64decode(X) | 对字段X的值执行base64解码，字段X必须为字符串 | 示例:…​ | eval base64 = base64decode(base64) |
| unicodeencode(X) | 对字段X的值执行unicode编码，字段X必须为字符串 | 示例:…​ | eval unicode = unicodeencode(unicode) |
| unicodedecode(X) | 对字段X的值执行unicode解码，字段X必须为字符串 | 示例:…​ | eval unicode = unicodedecode(unicode) |
| md5(X) | 对字段进行MD5编码 | 示例:…​ | eval a = md5(X) |
| sha1(X) | 对字段进行SHA1编码 | 示例:…​ | eval a = sha1(X) |
| sha256(X) | 对字段进行SHA256编码 | 示例:…​ | eval a = sha256(X) |
| sha512(X) | 对字段进行SHA512编码 | 示例:…​ | eval a = sha512(X) |
| ip2long(X) | 将ip地址转化为long类型的数字 | 示例:…​ | eval ipNum = ip2long(X) |
| long2ip(X) | 将long类型的数字转化为ip地址 | 示例:…​ | eval ip = long2ip(X) |
| cidr2long(X) | 将cidr路由转化为两个long类型的ip起止数字 | 示例:…​ | eval ip_range = cidr2long(X) |
| is_valid_mac(X) | 判断是否为有效的mac地址，目前只支持六组冒号或横杠分隔的地址 | 示例:…​ | eval is_valid_mac = is_valid_mac(X) |
| is_valid_ip(X) | 判断是否为有效的ip地址 | 示例:…​ | eval is_valid_ip = is_valid_ip(X) |
| is_valid_mask(X) | 判断是否为有效的子网掩码，在[0, 32]之间 | 示例:…​ | eval is_valid_mask = is_valid_mask(X) |
| is_valid_cidr(X) | 判断是否为有效的cidr地址 | 示例:…​ | eval is_valid_cidr = is_valid_cidr(X) |
| expand_ip_range_to_cidr(X, Y [,Z]) | 将两个ip起止地址转化为cidr地址，X为ip起始地址，Y为ip终止地址，Z为可选参数cleanSingleIps，如果是true代表mask是32的cidr会去掉mask，否则不去掉，默认为false。 | 示例:…​ | eval cidr = expand_ip_range_to_cidr("192.168.1.1", "192.168.1.15"); 或 …​ | eval cidr = expand_ip_range_to_cidr("192.168.1.1", "192.168.1.15", true)…​ | eval cidr = expand_ip_to_cidr(X); 或 …​ | eval cidr = expand_ip_to_cidr(X, true) |
| like(X, Y) | 接收两个参数，X为一个字符串，Y是一个表达式。当X与Y匹配时，此函数返回true,否则返回false。表达式Y支持精确文本匹配，以及单字符_和多字符%匹配。 | 示例:…​ | eval is_like = like(X, "a%bc") |
| isnotnull(X) | 判断是否不为null。当X不为null时，返回true | 示例:…​ | eval is_not_null = isnotnull(X) |
| isblank(X) | 判断是否为null或仅包含空白字符 | 示例:…​ | eval is_blank = isblank(X) |
| islong(X) | 判断是否为long类型字段 | 示例:…​ | eval is_long = islong(X) |
| isbool(X) | 判断是否为boolean类型字段 | 示例:…​ | eval is_bool = isbool(X) |
### 3.1. 搜索命令函数参数说明补充
#### 3.1.1. printf函数的format参数类型
由若干个转译字符（例如，整数d，字符串s，科学技术法g）组成，每个转义字符前可以包含可选项;（例如，flag字符，指明宽度精度）；"(%[flags][width][.precision]<conversion_specifier>)…​"
转译字符：
| 字符 | 参数类型 | 示例 |
| --- | --- | --- |
| 'b','B' | boolean变量 | 根据boolean参数输出true或false, "printf("%b",1==0.5+0.5), 输出 "true" |
| 's','S' | 字符串,输出string类型 | 内容与参数相同,printf("%s","spl"),输出"spl" |
| 'd' | 整数 | 将参数格式化为十进制整数输出,printf("%d",10),输出10 |
| 'o | 整数 | 将参数格式化为八进制整数输出,printf("%d",8),输出10 |
| 'x','X' | 整数 | 将参数格式化为十六进制整数输出,printf("%d",16),输出10 |
| 'e','E' | 整数或浮点数 | 将参数格式化为科学记数法输出,printf("%d",1248),输出1.248e3 |
| 'f' | 浮点数 | 输出参数的浮点数值 ,printf("%d", round(pi(),2)),输出3.14 |
| 'a','A' | 浮点数 | 参数格式化为十六进制浮点数输出,printf("%a",3.1415),输出 0x1.921cac083126fp1 |
| '%' | - | 百分号转译符,printf("%%"),输出% |
指定结果格式字符：
| 字符 | 描述 |
| --- | --- |
| '-' | 结果左对齐（默认右对齐） |
| '#' | 输出结果展示格式，例如printf("%#x",123) → 0x7b |
| '+' | 结构总是包含符号 |
| ' ' | 正数结果前有一个空格 |
| '0' | 结果用0补齐精度和宽度 |
#### 3.1.2. tonumber的参数类型
`tonumber(numStr)`语法：
| numStr类型 | 描述 | 结果 | 示例 |
| --- | --- | --- | --- |
| Number类型 - 数字 | 输入是数值类型的数字，则原样返回该数字。 | Number类型的数字 | tonumber(123) = 123 |
| String类型 - 基本类型（int, long, float, double) | 输入是基本类型数字字符串，则返回对应数字。（输入不支持L大小写表示的long值和f大小写表示的float值） | 基本类型对应数字 | tonumber("123") = 123;  tonumber("12345678910123456") = 12345678910123456L;  tonumber("1.23") = 1.23f;  tonumber("1.23456789") = 1.23456789 |
| String类型 - 超长 | 输入是超长整数或小数位数大于15位的数字，返回约等值。 | 约等值，可能会以科学计数法表示。 | tonumber("12345678901234567890") = 12345678901234567000;  tonumber("1.12345678901234567890") = 1.1234567890123457 |
| String类型 - 负数 | 输入是负数字符串，返回负数。 | 负数 | tonumber("-123") = -123;tonumber("-1.23") = -1.23f |
| String类型 - 科学计数法 | 输入是科学计数法表示的数字字符串，返回是对应的数值。 | 对应数值 | tonumber("1.234567890123e+12") = 1234567890123L |
| 表达式 | 输入是表达式，返回是表达式结果对应的数值。 | 对应结果数值 | tonumber(23 + 2) = 25;tonumber("23" + 2) = 232 |
`tonumber(numStr, base)`语法：
| numStr类型 | base范围 | 描述 | 结果 | 示例 |
| --- | --- | --- | --- | --- |
| 整数 – Number类型 | String类型（int, long）（包括负数) | 2-36 | 输入是2-36进制的数值类型的整数数字或数字字符串，返回转换为10进制后的整数数字。（输入不支持L大小写表示的long值，16进制支持0x开头字符串且字母大小写都支持） | Number类型的整数数字 | tonumber(123, 10) = 123;tonumber(123, 16) = 291;tonumber("123", 10) = 123;tonumber("1010", 2) = 10;tonumber("0xb5", 16) = 181;tonumber("-123", 10) = -123;tonumber("-123", 16) = -291 |
| 小数 - Number类型 | String类型（float, double）（包括负数) | 10 | 输入是10进制的数值类型的小数或小数字符串，才可返回该小数。（输入不支持f大小写表示的float值） | Number类型的小数数字 | tonumber(1.23, 10) = 1.23f;tonumber("1.23", 10) = 1.23f;tonumber("1.23456789", 10) = 1.23456789;tonumber("-1.23", 10) = -1.23f |
| 超长 | 2-36 | 输入是超长整数或小数位数大于15位的数字字符串，能解析成功就返回正常值，解析不成功不返回，结果超长返回约等值。（如果是小数字符串，只支持10进制） | 正常值 | 约等值 | 无值，可能会以科学计数法表示。 | tonumber("11111111111111111111", 10)= 11111111111111110000;tonumber("11111111111111111111", 2) = 1048575;tonumber("1.11111111111111", 10) = 1.11111111111111;tonumber("1.11111111111111111", 10) = 1.11111111111111112 |
| 科学计数法 | 10 | 输入是科学计数法表示的数字字符串，返回是对应的数值。 | 对应数值 | tonumber("1.12345e+5", 10) = 112345;tonumber("1.234567890123e-3", 10) = 0.001234567890123 |
| 表达式 | 2-36 | 输入是表达式，返回是表达式结果对应的数值。（如果结果是小数，只支持10进制） | 对应结果数值 | tonumber(2.3 + 2, 10) = 4.3 |
#### 3.1.3. in函数
in函数支持多种写法:
1. WHERE命令：```
（1）... | where in(field, V1, V2, ...)
（2）... | where field in(V1, V2, ...)
```复制
2. EVAL命令：```
（1）... | eval is_in = in(field, V1, V2, ...)
（2）... | eval is_in = if(in(field, V1, V2, ...), true, false)
```复制
详情:
| field | V系列 | 描述 | 示例 |
| --- | --- | --- | --- |
| 单值 | 若干指定值 | 如果field的值和V系列若干值中的任意一个相等，则返回true；否则，返回false。 | field = 1 → in(field, 1, 2) = true;field = 5 → in(field, 1, 2) = false; |
| 多值 | 若干指定值 | 如果field列表中的任一值和V系列人若干值中的任一值相等，则返回true；否则，返回false。 | field = [1,10,100] → in(field, 1, 2) = true;field = [1,10,100] → in(field, 11, 22) = false; |
| 单值或多值 | 无 | 如果V系列没有设置值，则都返回false; | field = 1 → in(field) = false; |
| 单值或多值 | 包含字段名 | 如果V系列中包含字段名，则使用字段值。其余规则同第一条。如果V系列中包含的字段名对应的也是多值，则不会平铺，按照列表比较。 | field = "1", value = "1" → in(field, value, "2") = true;field = ["1", "10", "100"], value = ["1", "11", "111"] → in(field, value) = false;field = ["1", "10", "100"], value = ["1", "10", "100"] → in(field, value) = true; |
| 单值或多值（数字） | 若干指定值（数字） | field和V系列是数字类型时，按值比较，相等即返回true，否则，返回false。（in和long，float和double） | field = 1L → in(field, 1, 2) = true;field = 1.5f → in(field, 1.5, 2.5) = true; |
## 4. 与stats有关的函数
**eval <expression>介绍**
：
1. 可以在通常使用<field>的统计函数中使用eval <expression>，此时必须使用`as newName`。
2. `| stats func(eval(<expression>)) as newName`等同于`| eval temp_field = <expression> | stats func(temp_field) as newName`.
3. 唯一的特殊情况，当统计函数为count(), 且expression结果为bool类型时，统计当结果仅为当expression为true的事件数。例如：`…​ | stats count(eval(status="404")) AS count_status BY sourcetype`, 统计的结果为status为404的事件总数。
**以下是可与stats等命令使用的统计函数，后续将扩展到其他的命令。约定**
：
- "X" 表示指定字段名， +
- "INTERVAL"表示指定时间间隔，描述方式如1m, 1d… 后缀有以下几种：y|M|w|d|h|m|s ， +
- "LIMIT"表示返回值的限制数量。
**分类**
：
- single函数：avg、count、distinct_count / estdc / dc、distinct、earliest、first、last、latest、max、min、rate、stddev、sum、sumsq、var
- multi函数：extend_stat / es、percentiles / pct、percentile_ranks / pct_ranks、skewness、kurtosis、covariance、correlation
- 画图函数：date_histogram / dhg、histogram / hg、range_bucket / rb、sparkline
- 其他：…​…​
| 函数 | 功能描述 | 示例 |
| --- | --- | --- |
| avg(X) | 返回字段X的平均值 | 返回平均响应时间：avg(response_time) |
| count[(X)] | 返回字段X的出现次数 | 返回status的个数：count(status) |
| date_histogram(X, INTERVAL)dhg(X, INTERVAL) | 时间直方图统计，可以认为是直方图统计的一种特殊形式 | 把timestamp字段以1h分桶统计：dhg(timestamp, 1h) |
| distinct(X) | 返回字段X的值去重后的的个数的精准值 | 返回字段clientip的唯一值值的个数的精确值：distinct(clientip) |
| distinct_count(X)estdc(X)dc(X) | 返回字段X的值去重后的个数的估计值 | 返回clientip的唯一值值的个数的估计值：dc(clientip) |
| earliest(X) | 返回字段X按照时间增序排序后的第一个值 | 返回appname字段按照时间增序排序后的第一个值：earliest(appname) |
| extend_stat(X)es(X) | 返回字段X的es扩展统计。es将返回多个值，将返回如下字段：_es.X.count_es.X.min_es.X.max_es.X.avg_es.X.sum_es.X.sum_of_squares_es.X.variance_es.X.std_deviation + | 返回resp_len字段的es统计值：es(resp_len) |
| first(X) | 返回数据中字段X的第一个出现的值 | 返回第一个appname的值：first(appname) |
| histogram(X, INTERVAL)hg(X, INTERVAL) | 直方图统计。字段X必须为整数类型 | 把apache.status以200分桶统计：hg(apache.status, 200) |
| last(X) | 返回字段X的最后一个出现的值 | 返回数据中最后一个appname的值：last(appname) |
| latest(X) | 返回字段X按照时间增序排序后的最后一个值 | 返回数据中的appname字段按照时间增序排序后的最后一个值：latest(appname) |
| list(X,[LIMIT]) | 将字段X的值组合成列表返回。LIMIT为值列表中值的个数上限，默认值为100 | 以下示例返回数据中appname出现的前90个值：*|stats list(appname,90) |
| mad(X) | 此函数将统计指定字段的绝对中位差(MAD)值 | 以下示例返回响应时间的绝对中位差(MAD)值:stats mad(response_time) |
| max(X) | 返回字段X的最大值字段X必须为数值类型 | 返回响应时间的最大值：max(response_time) |
| min(X) | 返回字段X的最小值字段X必须为数值类型 | 返回响应时间的最小值：min(response_time) |
| percentiles(X, Y1, Y2…​)pct(X, Y1, Y2…​) | 返回字段X的值排序后，百分位Y1, Y2所对应的字段值。pct将返回多个值，字段命名方式如下：Y1对应的字段为_pct.X.Y1Y2对应的字段为_pct.X.Y2…​…​ | 返回response_time在50%，75%, 95%分位的值：pct(response_time, 50, 75, 95)将返回三个字段：_pct.response_time.50,_pct.response_time.75,_pct.response_time.95 |
| percentile_ranks(X, Y1, Y2…​)pct_ranks(X, Y1, Y2…​) | 返回Y1，Y2所对应的百分位。X： 数值类型字段;Y1，Y2： 为字段X对应的值pct_ranks将返回多个值，字段命名方式如下：_pct_ranks.X.Y1_pct_ranks.X.Y2…​ | 以下示例返回100， 200， 500在response_time字段中对应的百分位：pct_ranks(response_time, 100, 200, 500)返回字段集合_pct_ranks.response_time.100_pct_ranks.response_time.200_pct_ranks.response_time.500 |
| range_bucket(RANGE_BUCKET, RANGE_BUCKET…​)rb(RANGE_BUCKET, RANGE_BUCKET…​) | X：为数值类型RANGE_BUCKET：统计区间，表示为(start, end)。可以设置多个。 | 以下示例把apache.status以指定区间分桶统计：rb(apache.status,(100,200) , (200,300), (300,400)) |
| rate(X) | 此函数将统计在指定时间跨度内指定字段值的变化速率。具体计算方法：(latest - earliest) / (latestT - earliestT)latest为字段X按照时间增序排序后的最后一个值earliest为字段X按照时间增序排序后的第一个值latestT为latest对应的timestampearliestT为earliest对应的timestamp | 返回数据中apache.resp_len值的变化速率：*|stats rate(apache.resp_len) |
| sparkline(agg(X), INTERVAL) | 按照指定区间分桶，通过面积图展示每个分桶内统计数据。agg：部分与stats有关的函数，支持所有的single函数 | 返回按1h分桶，按tag分类后，apache.resp_len的平均值对应的面积图：stats sparkline(avg(apache.resp_len), 1h) by tag |
| stddev(X) | 统计字段X的标准差字段X必须为数值类型 | 返回响应时间的标准差：stats stddev(response_time) |
| sum(X) | 返回字段X的值的和字段X必须为数值类型 | 返回响应长度的和：sum(response_len) |
| sumsq(X) | 统计字段X的平方和字段X必须为数值类型 | 返回响应时间的平方和：stats sumsq(response_time) |
| signify(X,[LIMIT]) | 返回指定字段中有趣或不寻常的字段值的集合，并按照重要性排序。 字段值的重要性取决于score的大小。示例：用户在文本中搜索“禽流感”时提示“H5N1”；发现欺诈性医生诊断出的鞭伤伤害超过了他们的公平份额；发现爆胎次数不成比例的轮胎制造商。在所有这些情况下，所选择的术语不仅仅是一组中最流行的术语。 它们是在前景和背景集之间测量的流行度发生显着变化的术语。 如果术语“H5N1”仅存在于 1000 万个文档索引中的 5 个文档中，但在构成用户搜索结果的 100 个文档中的 4 个中找到，这些文档很重要并且可能与他们的搜索非常相关。 5/10,000,000 对 4/100 是一个很大的频率摆动。打分的原理是根据foregroundPercent(目标术语在前景集所占的百分比)与backgroundPercen(目标术语在背景集所占的百分比)计算得分，前景集：与查询直接匹配的搜索结果；背景集：从中检索它们的索引；目标术语：用户感兴趣的、重要的术语 重要术语聚合的任务是比较这些集合并找到最常与用户查询关联的术语。LIMIT默认值为10。 | 返回目标字段appname对应的值中最重要的10个。此例中appname为前景集，query语句查询的内容为背景集，返回的结果为目标术语。*|stats signify(appname,10) |
| top(X, LIMIT) | 此函数统计字段X内最多出现的若干个值 + | 返回apache.status使用最多的三个值及其对应使用的次数：top(apache.status, 3) |
| values(X,[LIMIT]) | 返回字段X去重后的值。LIMIT默认值为100 | 以下示例返回数据中appname出现的前90个不重复的值：*|stats values(appname,90) |
| var(X) | 统计字段X的方差字段X必须为数值类型 | 返回响应时间的方差：stats var(response_time) |
| skewness(X1, X2…​) | 返回字段X1, X2…​的偏度，字段X1, X2…​必须为数值类型，该函数支持多字段。 | 返回响应时间的偏度：stats skewness(response_time)返回响应时间和响应长度的偏度：stats skewness(response_time, response_len) |
| kurtosis(X1, X2…​) | 返回字段X1, X2…​的峰度，字段X1, X2…​必须为数值类型，该函数支持多字段。 | 返回响应时间的峰度：stats kurtosis(response_time)返回响应时间和响应长度的峰度：stats kurtosis(response_time, response_len) |
| covariance(X1, X2…​) | 返回字段X1, X2…​的协方差，字段X1, X2…​必须为数值类型，该函数需要至少两个字段。 | 返回响应时间和响应长度的协方差：stats covariance(response_time, response_len) |
| correlation(X1, X2…​) | 返回字段X1, X2…​的相关系数，字段X1, X2…​必须为数值类型，该函数需要至少两个字段。 | 返回响应时间和响应长度的相关系数：stats correlation(response_time, response_len) |
| derivative(X,T) | 统计桶间的字段X根据时间字段T的变化速率具体计算方法：(currentX - previousX) / (currentT - previousT)currentX为当前桶的字段XpreviousX为上一个桶的字段XcurrentT为当前桶的时间字段TpreviousT为上一个桶的时间字段T | 返回当前桶和上一个桶的指定字段值的变化速率streamstats derivative(value, ts) |
## 5. 常见的时间和时间格式
### 5.1. 时间格式
日期和时间格式可以通过时间和日期的模式字符串来指定。日期和时间的模式字符串中，未转义的字符A-Z以及a-z将被解释一个模式字符，用于表示日期和时间字符串的组成部分。文本可以通过使用单引号括起来避免被解释，双单引号则用于表示单个单引号。其他的任何字符都不会被解释，将直接被输出到目标的日期和时间字符串。
以下列出定义的模式字符（所有其他A-Z和a-z之间的字符暂时被保留）
| 字符 | 日期和时间的组成部分 | 描述 | 示例 |
| --- | --- | --- | --- |
| G | Era Designator | 文本 | Ad  (公元) |
| C | Centry of era(>=0) | Year | 20 |
| Y | Year of ear(>=0) | Year | 1996 |
| x | Week year | year | 1996 |
| w | Week of year | number | 27 |
| e | Day of week | number | 2 |
| E | Day of week | text | Tuesday; Tue |
| y | Year（年） | Year(年) | 1996；96 |
| M | Month in year（月份） | Month(月份) | July，Jul，07 |
| W | Week in month(当月第几周) | Number | 2 |
| D | Day in year (当年第几天) | Number | 190 |
| d | Day in month (当月第几天) | Number | 28 |
| a | Halfday of day | text | PM, AM |
| K | Hour of halfday(0-11) | number | 0 |
| h | Clockhour of halfday(1-12) | Number | 12 |
| H | Hour in day (0-23) | Number | 0 |
| k | Hour in day (1-24) | Number | 24 |
| K | Hour in am/pm (0-11) | Number | 0 |
| m | Minute in hour (0-59) | Number | 30 |
| s | Second in minute (0-59) | Number | 59 |
| S | Millisecond(毫秒) | Number | 988 |
| z | Time zone | 通用时区 |  |
| Z | Time zone | RFC 822时区 | -0800；+0800 |
| ' | Escape for text | delimiter | -08；-0800； -08:00 |
模式字符大多是多个重复出现，出现的个数可精确表示其形式
- Text: 如果模式字符的个数大于等于4，将输出完整的形式，如果小于4且存在可用的简写形式，则输出简写形式
- Number：模式字符的个数表示输出格式最少的数字个数，如果模式字符的个数大于实际输出的数字个数，则采用0进行填充，比如模式为MM，而实际月份为1月，则输出01
- Month：如果模式字符个数大于3，则月份将使用文本形式，否则使用数字形式，如MMM输出为Jul，MMMM则输出July
- Year：如果模式字符个数为2，year将输出为2个数字，比如09，16如果模式字符个数为4，year将被输出为4个字符，比如2009，2016
| 时间日期模式 | 时间和日期 |
| --- | --- |
| "G yyyy-MM-dd HH:mm:ss" | AD 2016-01-01 12:03:01 |
| "EEE, d/MMM/yy" | Wed, 4/Jul/01 |
| "EEEE,dd/MMMM/yyyyy HH:mm:ss Z" | Tuesday,03/July/02001 12:03:01 -0700 |
### 5.2. 与搜索结合使用的时间修饰符
你可以使用时间修饰符来自定义搜索的时间范围，比如说，可以指定搜索的开始时间和结束时间
绝对时间修饰符
绝对时间由日期和时间组成，格式如下:
```
yyyy-MM-dd:HH:mm:ss
```
复制
示例1：
```
2015-01-02:12:33:21
```
复制
|  | 注意日期和时间之间有冒号 |
| --- | --- |
相对时间修饰符
```
可使用表示时间量(整数和单位)和对齐到时间单位（可选）的字符串在搜索中定义相对时间。
```
复制
语法：
```
" [now]((+|-)<time_integer><time_unit>(/<time_unit>)?)*"
```
复制
1. 在字符串的前面机上加号(+)和减号(-)表示与当前时间的偏移
2. 使用数字和单位定义时间量；支持的时间单位为：- 秒：  s、sec、secs、second、seconds
- 分钟：m、min、mins、minute、minutes
- 小时：h、H、hr、hrs、hour、hours
- 天：  d、day、days
- 周：  w、week、weeks
- 月：  M、mon、month、months
- 季度：q、qtr、qtrs、quarter、quarters
- 年：  y、year、years
- 交易日：t
|  | 交易日计算：如果用户搜索-1t，用户并没有提供对应的交易日列表，则报错提示找不到该domain的交易日信息。如果用户搜索-1t，用户提供的交易日范围大于1t的话则返回正常的交易日对应的自然日日期。如果用户搜索-10t，用户提供的只到-3t的话就返回-3t对应的时间戳并提示交易日计算异常。-1t/t的作用就是找到当天交易日，计算出当天交易日的零点；也就是-1t/d的作用 |
| --- | --- |
示例1： "-2d/d"
```
前天的零点零分零秒
```
复制
示例2： "now-1M/M-1d/w"
```
当前时间减去一个月，取整到月，再减去一天，按周取整，具体表示上上个月的最后一周的开始
```
复制
示例3： "now"
```
当前时间
```
复制
## 6. 检索指令
### 6.1. search
search命令的query参数描述对原始日志的搜索条件，在第一个管道前边时从索引取数据，不需要加命令名字，在管道之后位置相当于where
语法：  这里采用类似巴克斯范式描述
```
[index=<index>] [starttime=<time-modifier>] [endtime=<time-modifier>] [now=<time-modifier>] <query>
```
复制
<query>: :  <or-clause> (OR <or-clause>)*
<or-clause>: : <and-clause> (AND <and-clause>)*
<and-clause>: :  "(" <query> ")" | NOT <query-term> |<query-term>
<query-term>: : [<field>:] <term> | <sub-pipe>
<sub-pipe>: :  "[[" <pipe-commands> "]]"
<term>: : <simple-term>|<wild-term>|<prefix-term>|<regex-term>|<range>
语法单元解释：
- index语法：```
<string>
```复制描述：```
指定所需搜索的索引，目前支持schedule, yotta，默认为yotta
```复制示例：```
index=schedule
```复制
- starttime语法：```
<time-modifier>
```复制描述：```
格式请参考时间修饰符一节，表示搜索的时间区间的开始，包括该时间
```复制示例：```
starttime=2018-09-01
```复制
- endtime:语法：```
<time-modifier>
```复制描述：```
格式请参考时间修饰符一节，表示搜索的时间区间的结束，不包括该时间
```复制示例：```
endtime=2018-09-01
```复制NOTE：```
如果query中指定了starttime和endtime，则使用该时间区间，忽略页面中指定的时间区间。
```复制
- now:语法：```
<time-modifier>
```复制描述：```
格式请参考时间修饰符一节，表示搜索的时间区间的结束，不包括该时间
```复制示例：```
now=2018-09-01
```复制NOTE：```
如果指定了now，并且starttime和endtime中有相对时间，则starttime和endtime的绝对时间是基于now来计算的，如果now是相对时间，则now是先基于当前时间计算出now的绝对时间，然后基于now的绝对时间再计算出starttime以及endtime。
```复制
- query-term语法：```
[<field>:]<term>
```复制描述：```
field部分为可选，如果不写field，则默认field为raw_message，支持通配符
```复制
- term:语法：```
<pharse-term> | <wild-term> | <regex-term> | <range> | <simple-term>
```复制描述：```
指定某个字段中的查询条件，支持通配符，正则表达式，range，短语查询
```复制参数：phrase-term语法：```
"<string>"
```复制描述：```
放在双引号内的查询表示短语查询
示例："http://rizhiyi.com/"
```复制wild-term:描述：```
通配符查询，查询中的?表示匹配单个字符，*表示匹配多个字符
```复制NOTE：```
这里不支持指定标点符号及特殊字符的匹配，例如qu-*
```复制示例：```
qu?ck*
```复制regex-term:语法：```
/<string>/
```复制描述：```
正则表示式
```复制示例：```
name: /joh?n(ath[oa]n)/
```复制range:语法：```
( [ | { ) <value> TO <value> (} | ])
```复制描述：```
使用中括号和大括号来描述一个range，中括号表示包含，大括号表示不包含，<value>可以是数值或者字符串，也可以使用>=这种写法
```复制示例：count值在1到5之间，包括1和5。其写法为：count: [1 TO 5] 或者 count: >=1 AND count: ⇐5count值大于等于10。其写法为：count: [10 TO *] 或者 count: >= 10年龄小于10。其写法为：age: <10年龄小于等于10。其写法为：age: ⇐ 10年龄大于10。其写法为：age: >10simple-term:语法：```
string
```复制描述：```
不包含在双引号中的字符串，保留字符需要转义
```复制
**保留字符**
如果你在query中包含以下保留字符，则需要进行转义：使用反斜杠转义
```
+ - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ / |
```
复制
由于空格是query各个部分的分割符，如果query包含空格请使用反斜杠转
**多索引查询的支持**
1.通配符支持
指定index的时候，支持通配符*号和?号
- 示例1：index=mai* ERROR | …​```
在所有mai为前缀的索引返回包含ERROR关键字的日志，比如main，mail索引等等
```复制
- 示例2：index=*  ERROR```
    不会查询schedule索引
      
* 示例3：index=*,schedule ERROR
```复制```
则查询schedule索引（内置索引）和其他用户索引索引
```复制
|  | 如果指定的索引包含通配符，是不会尝试匹配内置索引的（schedule等），如果希望查询schedule索引，必须明确指定schedule索引由于搜索页面仅显示部分数据，所以我们指定在返回非统计查询的的最大返回结果数为1000用于页面展示，如果需要查看全量数据，请下载当次搜索的数据查看，其对应的配置项为query.max_result_count |
| --- | --- |
2.多个索引的支持
逗号分割的索引列表，不要包含空格
```
index=apache,nginx ERROR | ...
```
复制
在apache和nginx的索引中返回包含ERROR关键字的日志
3.多个query的支持
```
(index=apache starttime="now/d" endtime = "now"upstream_time:>300) OR ( index=nginx starttime="-1d/d" endtime="now/d" upstream_time:>200)
```
复制
apache索引中搜索今天upstream_time大于300的日志，以及nginx索引中搜索昨天upstream:>200的日志
- 示例1： logtype为apache，并且apache.req_time大于0.05秒```
( host: localhost OR host: 127.0.0.1 ) OR apache.req_time: >0.05 | ...
```复制
- 示例2：ip地址以10.开头，或者192.开头的所有ip```
ip: 10.* OR ip:192.* | ...
```复制
- 示例3：搜索schedule索引，昨天一整天的数据，schedule_name为hour_logsize```
index=schedule starttime="-1d/d" endtime="now/d" schedule_name:hour_logsize
```复制
- 示例4: 搜索所有数据，相当于 *```
 | search *
```复制
- 示例5: 过滤appname字段=apache的日志
```
 ... | search appname:apache
```
复制
- 示例6: 过滤以name结尾的字段=apache的日志```
[source,bash]
 ... | search *name:apache
```复制
### 6.2. multisearch
摘要：
```
同时执行多个搜索，把搜索结果合并起来。需要至少两个子查询
```
复制
语法：
```
multisearch [[ <subsearch> ]] [[ <subsearch> ]]...
```
复制
必要参数：
- subsearch语法```
<sub-pipeline>
```复制描述```
子查询，支持管道分隔的分布式流式命令
```复制
Example 1. 示例1
同时搜索yotta索引里appname是apache的日志，和metric索引里appname是json的日志，并提取出来同名的clientip字段
```
 | multisearch [[ _index:yotta appname:apache | eval clientip=apache.clientip ]] [[ _index:metric appname:json | eval clientip=json.sourceip  ]]
```
复制
### 6.3. addinfo
摘要：
```
向每个事件添加包含有关搜索的全局通用信息的字段，如下表所示：
```
复制
| 字段名 | 含义 |
| --- | --- |
| info_min_time | 搜索时间范围的起始时间 |
| info_max_time | 搜索时间范围的结束时间 |
| info_sid | 事件所属搜索任务的sid |
| info_search_time | 事件所属搜索任务的运行时间 |
语法：
```
addinfo
```
复制
Example 2. 示例：
取搜索结果第一条添加上全局通用信息的字段
```
* | limit 1 | addinfo
```
复制
### 6.4. append
摘要：
```
append命令允许通过将子管道命令的结果附加在主管道之后，达到合并两个管道结果的目的
```
复制
语法：
```
append <sub-pipeline>
```
复制
必要参数：
- sub-pipeline语法```
<结果的列表>
```复制描述```
子查询 SPL 语句
```复制
Example 3. 示例：
分别统计大前天和昨天的响应消息长度的平均值
```
 starttime="-3d/d" endtime="-2d/d" * | stats avg(apache.resp_len) | eval day="the day before yesterday" | append [[ starttime="-1d/d" endtime="now/d" * | stats avg(apache.resp_len) | eval day="yesterday" ]]
```
复制
主管道统计大前天的平均响应长度，append命令中子管道统计昨天的平均值，其结果合并在一张结果的表中
### 6.5. union
摘要：
```
同时执行多个搜索，把搜索结果合并起来。需要至少两个子查询。可以分布式执行命令的命令相当于multisearch命令，其他命令相当于append命令
```
复制
语法：
```
union [[ <sub-pipeline> ]] [[ <sub-pipeline> ]]...
```
复制
必要参数：
- sub-pipeline语法```
<sub-pipe>
```复制描述```
子查询，支持管道分隔的命令
```复制
Example 4. 示例1
同时搜索yotta索引里appname是apache的日志，和metric索引里appname是json的日志，并提取出来同名的clientip字段
```
 | union [[ _index:yotta appname:apache | eval clientip=apache.clientip ]] [[ _index:metric appname:json | eval clientip=json.sourceip  ]]
```
复制
Example 5. 示例2
分别统计yotta索引和metric索引里的结果数
```
 | union [[ _index:yotta | stats count() | eval index="yotta" ]] [[ _index:metric | stats count() | eval index="metric" ]]
```
复制
### 6.6. appendcols
摘要：
```
添加一个子搜索，并将子搜索的结果按顺序合并到父搜索上
```
复制
语法：
```
appendcols param-options* [[ subsearch ]]
```
复制
可选参数：
- param-options语法```
<override> | <maxout>
```复制参数override语法```
override = <bool>
```复制描述```
子搜索中的同名字段是否覆盖父搜索的字段值，默认为false
```复制maxout语法```
maxout = <int>
```复制描述```
子搜索的最大返回条数，默认为50000
```复制
- subsearch语法```
<sub-pipeline>
```复制描述```
子查询语句
```复制
|  | 如上的maxout参数值有上限值，默认为200000；对应的配置项为 appendcols.max_out_limit |
| --- | --- |
Example 6. 示例：
查询2019-12-04日至2019-12-06日的结果并且将该时间范围统计出来的count数追加到第一行结果中
```
* | appendcols override=false maxout=10 [[ * | stats count() as cnt]]
```
复制
### 6.7. autoregress
摘要：
```
将当前事件之前的事件中的字段值拷贝到当前事件，该字段可以用于后续的表达式计算等。
```
复制
语法：
```
autoregress <field>[ as <as-field> ] p=<num>|<num>-<num>
```
复制
必要参数：
- field语法```
<field>|<single-quoted-string>
```复制描述```
事件中需要拷贝的字段，大多情况下是数值字段。
```复制
- p语法```
p=<number>
```复制描述```
表示当前事件之前的那些事件的字段将被拷贝到当前事件，可以指定为单个数字或者数字的范围，如果指定为单个数字，比如p=3，当前事件之前的第三条事件的字段将被拷贝，如果指定为数字的范围，比如p=2-4，则表示当前事件之前的第四条到第二条事件都将被拷贝到当前事件，并采用一定的命名规则命名。
```复制
可选参数：
- as-field语法```
<field>|<single-quoted-string>
```复制描述```
仅当p指定为单个数字的时候，as-field表示目标的字段名，否则目标字段名为<field>_p<num>这种形式，比如p=2-3，则产生两个新的字段名: <field>_p2, <field>_p3
```复制
Example 7. 示例
按小时统计事件数，并计算出当前小时和上个小时的事件数变化比率
```
* | bucket timestamp span=1h as ts | stats count() as count_ by ts | autoregress count_ as last_count  p=1 |eval a=(last_count - count_)/count_ | eval change_rate = format("%.3f%%", (last_count - count_)*100/count_)
```
复制
### 6.8. bucket
摘要：
```
将字段中连续的数字值，放入离散集的数据桶中，该变量可用于后续的stats等命令的分组字段中
```
复制
语法：
```
bucket <field> <bucketing-option> [as <field>]
```
复制
必要参数：
- bucket-option语法```
span | ranges | timeranges
```复制描述```
离散化选项
```复制参数bucket-span语法```
span = <span-length>
```复制描述```
使用基于时间或者绝对数值的长度设置每个数据桶的大小
```复制参数span-length语法```
<int>[<timeunit>]
```复制描述```
每个数据桶的跨度，第一个数字为系数，如果提供了timeunit，这将被视为时间范 围，否则这是一个绝对数值的桶的跨度
```复制参数timeunit语法```
s | m | h | d | w | M
```复制描述```
时间单位，分别表示秒，分钟，小时，天，周，月（更多扩展写法详见小节'与搜索结合使用的修饰符')
```复制bucket-timeranges语法```
timeranges = <time-ranges>
```复制描述```
使用时间修饰符指定一组时间的区间，ranges也通过左闭右开的区间
```复制参数date_ranges语法```
( ([MIN], <time>), (<time>, <time>)*, (<time>, [MAX]) )
```复制描述参数time语法```
<date>|<datetime>|<string>|<date-relative>
```复制参数date语法```
\d{4}-\d{2}-\d{2}
```复制datetime语法```
<date>:\d{2}:\d{2}:\d{2}
```复制date-relative语法```
-<span-length>
```复制参数span-length语法```
<int>[<timeunit>]
```复制描述```
每个数据桶的跨度，第一个数字为系数，如果提供了timeunit，这将被视为时间范 围，否则这是一个绝对数值的桶的跨度
```复制参数timeunit语法```
s | m | h | d | w | M | y
```复制描述```
时间单位，分别表示秒，分钟，小时，天，周，月，年
```复制bucket-ranges语法```
ranges = <number-ranges>
```复制描述```
通过数值对来指定一组range，MIN表示最小值，MAX为最大值，均为可选，所 有的range均为左闭右开的区间，形式化的描述为[<number>, <number>]，包括第一个值，但小于第二个值
```复制参数number-ranges语法```
( ([MIN], <number>), (<number>, <number>)*, (<number>, [MAX]))
```复制描述```
使用时间修饰符指定一组时间的区间，ranges也通过左闭右开的区间
```复制
可选参数：
- field语法```
<field>
```复制描述```
指定一个字段名称, 如果未指定，则使用原始字段名称
```复制
Example 8. 示例1
返回每1小时跨度内的每个hostname的apache.resp_len的平均值
```
logtype:apache | bucket timestamp span=1h as ts | stats avg(apache.resp_len) by hostname, ts | eval ts_human = formatdate(ts)
```
复制
Example 9. 示例2
返回apache.status为100-200， 200-400， 400以上的apache.status的个数
```
logtype:apache | bucket apache.status ranges=((100, 200), (200, 400), (400,)) as rs | stats count(apache.status) by rs
```
复制
### 6.9. composite
摘要：
```
优化版的stats，一定情况下可减少部分内存使用，使用方法完全相同。与stats的性能对比：无byField时，与stats相同；单byField时，增加少量时间消耗；多byField时，增加少量时间消耗，减少部分内存使用。
```
复制
语法：
```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | list | values | top | es | dhg | hg | pct | pct_ranks | rb | sparkline | mad
```
复制
可选参数：
- field语法```
<field> | <single-quoted-string>
```复制描述```
每个stats_function都可以定义输出字段名，否则对后续的计算不可见
```复制
- stats_function语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | mad
```复制描述```
与stats命令结合的函数，请参考[#与stats有关的函数]
```复制
- field-list语法```
<field> | <single-quoted-string>
```复制描述```
分组字段，所有的stats_func将在分组内统计
```复制
Example 10. 示例1
统计state和pid的组合的事件数量
```
logtype:json | composite count() by json.state, json.pid
```
复制
### 6.10. chart
摘要：
```
按照over字段进行分桶后的统计行为
```
复制
语法：
```
chart [<chart-params>]* <stats-single-value-func> [<stats-single-value-func>]* [over <field> <chart-over-params>*] [by <field> <chart-by-params>*]
```
复制
必要参数：
- stats-single-value-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | mad | top
```复制描述```
用于统计的函数
```复制
可选参数：
- chart-params语法```
[sep=<string>] | [format=<string>] | [cont=<bool>] | [limit=<int>] | [rendertype=<string>]
```复制参数sep语法```
sep=<string>
```复制描述```
表示by field和统计字段组合时的分隔符，默认值为":"。这里默认的顺序为统计字段+分隔符+byfield，如果想改变顺序，请使用下面format参数
```复制format语法```
format=<string>
```复制描述```
表示规定字段的组合分隔符和组合顺序，默认值为"$AGG:$VAL"。 在这个字段中用$AGG表示统计字段，$VAL表示by field的值，所以一般的写法是format="$AGG$VAL"，此时为字段分隔符，如果想改变组合顺序，可将$VAL和$AGG的顺序反过来，分隔符仍需置于中间位置
```复制cont语法```
cont=<bool>
```复制描述```
表示是否将不连续的时间桶补充为连续，默认为false。因为将时间按照一定的时间间隔进行分桶时，有些桶内可能没有日志或者时间落入桶，此时桶内的所有统计值都为0。默认情况下会将这些桶所在的行去掉，如果置为true则会将这些行补充到结果中。
```复制limit语法```
limit=<int>
```复制描述```
表示限制使用by field值的个数，默认值为无穷大。即若语句中有 max count avg三种统计函数，by field有10种值，那么在不限制limit的情况下将有3*10+1个字段，即结果中有31列。若limit=5，那么将只取byfield的前5个值与统计字段进行组合，结果就只有3*5+1=16列，结果中也将只有这些列的值。
```复制rendertype语法```
rendertype=<string>
```复制描述```
可选值：pie(环形图)，rose(玫瑰图)，bar(条形图)，sunburst(旭日图)，sankey(桑基图)，force(力图)，chord(和弦图)，heatmap(热力地图)，wordcloud(词云图)。维度图包含：pie，rose，bar。可同时有over和by字段，或只有任一字段。当同时有两个字段时，会将over的字段与by平铺的字段拼接绘图展示（sunburst除外，只能有两个字段，直接层级展示）；关系图包含：sankey，force，chord。必须同时有over和by字段，over为来源字段，by为目的字段；其他：heatmap，wordcloud。只能有over或by其中一个字段，做切分使用
```复制
- chart-over-params语法```
[bins=<int>] | [span=<SPAN>] | [startindex=<int>] | [endindex=<int>]
```复制参数span-str语法```
span=<string>
```复制描述```
表示分桶间隔，格式为数字或数字+单位，与bucket指令span参数的格式相同，单位可以是 s | m | h | d | M（更多扩展写法详见小节'与搜索结合使用的修饰符')
```复制bins语法```
bins=<int>
```复制描述```
表示最多有多少个桶，默认值100。
```复制startindex语法```
startindex=<int>
```复制描述```
默认值为0，表示从所有桶中的第几个桶开始取，前面的桶对应的行将被舍弃
```复制endindex语法```
endindex=<int>
```复制描述```
默认值为无穷大，表示取到所有桶中的第几个桶，后面的桶对应的行将被舍弃
```复制
- chart-by-params语法```
[bins=<int>] | [span=<SPAN>] | [startindex=<int>] | [endindex=<int>]
```复制参数bins语法```
bins=<int>
```复制描述```
表示最多有多少个桶，默认值100。
```复制span语法```
span=<string>
```复制描述```
表示分桶间隔，格式为数字或数字+单位，与bucket指令span参数的格式相同
```复制startindex语法```
startindex=<int>
```复制描述```
默认值为0，表示从所有桶中的第几个桶开始取，前面的桶对应的行将被舍弃
```复制endindex语法```
endindex=<int>
```复制描述```
默认值为无穷大，表示取到所有桶中的第几个桶，后面的桶对应的行将被舍弃
```复制
|  | 由于chart支持按照多个字段进行分组,所以这里会与stats命令中的by字段有同样的限制，详情见stats命令的NOTE中的group.size以及stats.oneby.group_size配置项 |
| --- | --- |
Example 11. 示例1
字段分割符为**，组合顺序为byfield值+分隔符+统计字段，限制byfield值为5个进行组合，桶最大个数为10个，分桶为1小时一个，按照agent_send_timestamp进行分组后的结果，collector_recv_timestamp分组间隔为50s，最多分为20个桶，取第四到第六个桶值
```
* | chart sep="," format="$VAL**$AGG" limit=5 cont=true count() over agent_send_timestamp bins=10 span="1h" by collector_recv_timestamp span="50s" bins=20 startindex=4 endindex=7
```
复制
Example 12. 示例2
字段分割符为**，组合顺序为byfield值+分隔符+统计字段，限制byfield值为5个进行组合，按照apache.status进行分组后的结果统计apache.x_forward的次数
```
* | chart sep="," format="$VAL**$AGG" limit=5 cont=false rendertype="pie" count(apache.x_forward) over apache.status
```
复制
### 6.11. collect
摘要：
```
将查询的结果写到索引，需要有运行collect命令的权限
```
复制
语法：
```
collect index=<field> [marker="<key>=<value>, <key>=<value> ..."] [testmode=<bool>]
```
复制
必要参数：
- index语法```
index=<field>|<double-quoted-string>
```复制描述```
要写入的索引名。索引在"路由配置"中查看和添加。索引必须存在，当前用户必须有索引写权限
```复制
可选参数：
- marker语法```
marker=<key>=<value>, <key>=<value> ...
```复制描述```
写入结果中追加对键值对。kv格式的键值对，kv键值对，k和v用等号(=)分隔，kv对儿之间用逗号(,)分隔
```复制
- testmode语法```
testmode=<bool>
```复制描述```
是否是用test模式运行，test模式不写入索引，默认为false
```复制
Example 13. 示例
把搜索的结果写入test索引，修改appname为test，tag为tag1
```
*|collect index=test marker="appname=\"test\", tag=\"tag1\""
```
复制
### 6.12. correlation
摘要：
```
按照bucket指定的分桶方式，计算搜索结果如arr_all=[100,3213,421]和每个字段对应的每个值的统计值如arr_k1_v1=[31,1030,123]，再根据pearson算法计算两个数组的相关性，保留每个字段的相关性最高的值，并给出范围在[-1, 1]之间的相关性得分
```
复制
语法：
```
correlation <bucket-field>
```
复制
可选参数：
- bucket-field语法```
bucket_field = <field>
```复制描述```
参数值为使用bucket命令的range参数指定分桶信息的字段
```复制
- excludeone语法```
excludeone = <boolean>
```复制描述```
默认值为true。当background dataset与命中数据在指定的分桶上的结果相同且唯一时，相关性结果为1，指定该参数为true时，过滤这样的结果。例如，`status:error`为bg dataset，`status:error appname:SPL`, 如果appname只有一个值为value时，该结果就可以被过滤
```复制
Example 14. 示例1
按照bucket指定的分桶，查询与状态为error的相关性高的字段与对应的字段值
```
error
| where !isnull(json.duration)
| bucket json.duration ranges=((0,500),(500,1000),(1000,20000),(20000,40000),(40000,60000),(60000,80000),(80000,100000),(100000,200000),(200000,400000),(400000,600000),(600000,800000),(800000,1000000),(1000000,2000000),(2000000,4000000),(4000000,6000000),(6000000,)) as rs
| correlation bucket_field=rs
| sort by correlation
```
复制
### 6.13. dbxexec
摘要：
```
是一个可以使用sql来更新/删除远程数据的数据
```
复制
语法：
```
dbxexec <connection> <param-options>* <query> [<params>]
```
复制
必要参数：
- connection语法```
connection = <string>
```复制描述```
指的是数据源名称(该数据源是配置页面配置好的)
```复制
- query语法```
query = <string>
```复制描述```
使用的sql语句或者其他数据库支持的更新/删除语句
```复制
可选参数：
- param-options语法```
<batchsize> | <timeout>
```复制描述```
可选参数选项
```复制参数batchsize语法```
batchsize = <int>
```复制描述```
查询时分batch取数据，每个batch的大小，默认为100
```复制timeout语法```
timeout = <int>
```复制描述```
query查询超时时间(单位为秒)，默认为600
```复制
- params语法```
params = <field>[,<field>]*
```复制描述```
用于query中替换的字段值
```复制
Example 15. 示例1
更新connection配置为110test的数据源对应的dbxexec_test表中当id为前序字段值的数据为前序count字段值
```
dbxexec connection="110test" query="update dbxexec_test set count=? where id=?" params=count,id
```
复制
搜索数据结果：
### 6.14. dbxlookup
摘要：
```
类似sql的连接，将来自远程数据库表的结果和子管道的结果连接在一起
```
复制
语法：
```
dbxlookup [<chunksize>] (<preset-lookup-option> | <lookup-option>)
```
复制
必要参数：
- preset-lookup-option语法```
<lookup>
```复制参数lookup语法```
lookup = <string>
```复制描述```
指的是已配置的lookup名称(该名称是dbxlookup配置页面配置好的)
```复制
可选参数：
- chunksize语法```
chunksize = <int>
```复制描述```
指定分批查询数据的条数batch_size
```复制
- lookup-option语法```
<lookup-field-list> <connection> <query> ON <join-field-list>
```复制参数lookup-field-list语法```
<field> [as <field>] (, <field> [as <field>])*
```复制描述```
指定将远程数据库中的数据保留在搜索结果中的字段列表
```复制connection语法```
connection = <string>
```复制描述```
指的是数据源名称(该数据源是配置页面配置好的)
```复制query语法```
query = <string>
```复制描述```
使用的sql语句或者其他数据库支持的查询语句
```复制join-field-list语法```
<field> = <field> (, <field> = <field>)*
```复制描述```
等号左边的field表示主结果中的字段，等号右边的field为远程数据库搜索结果中的字段
```复制
|  | dbxlookup命令每个batch的最大条数的上限默认为10000条，对应配置项为dbxquery.max_fetch_size |
| --- | --- |
Example 16. 示例
将模拟的数据与已配置lookup名称为gc_test_vertica的数据连接在一起
```
|makeresults count=1 | eval hostname="TEST" | dbxlookup lookup="gc_test_vertica"
```
复制
搜索数据结果：
Example 17. 示例
将模拟的数据与connection配置为221_test_vertica的数据源的结果中的id和ttime字段通过hostname和text字段进行join并返回的结果
```
|makeresults count=1 | eval hostname="TEST"| dbxlookup id,ttime connection="221_test_vertica" query="SELECT * FROM test.test" on hostname=text
```
复制
搜索数据结果：
### 6.15. dbxoutput
摘要：
```
将当前搜索的数据按照已配置的dbxoutput名称写出到远程数据库
```
复制
语法：
```
dbxoutput <output>
```
复制
必要参数：
- output语法```
output=<string>
```复制描述```
指的是output名称(该名称是dbxoutput配置页面配置好的)
```复制
Example 18. 示例1
将模拟数据输出到output配置为output1对应的远程数据库中的指定字段中。
```
|makeresults count=1 | eval appname="ccccc" |eval id=1002 |dbxoutput output="output1"
```
复制
搜索数据结果：
### 6.16. dbxquery
摘要：
```
是一个可以使用sql来查远程数据库的数据并作为spl的查询语句的命令（不支持跨库联查，如果要使用两个库的话可以使用append，join等）
```
复制
语法：
```
dbxquery connection <dbx-params>* <dbx-query-procedure> [ params=<string>[,<string>]* ]
```
复制
必要参数：
- connection语法```
connection=<string>
```复制描述```
指的是数据源名称(该数据源是配置页面配置好的)
```复制
- dbx-query-procedure语法```
<query> | <procedure>
```复制参数query语法```
query = <string>
```复制描述```
使用的sql语句或者其他数据库支持的查询语句
```复制procedure语法```
procedure = <string>
```复制描述```
指的是使用存储过程，支持params
```复制
可选参数：
- dbx-params语法```
<fetchsize> | <maxrows> | <timeout> | <shortnames>
```复制参数fetchsize语法```
fetchsize = <int>
```复制描述```
查询时分batch取数据，每个batch的大小，默认为10000
```复制maxrows语法```
maxrows = <int>
```复制描述```
该查询语句所能查到的所有数据的条数限制，默认为100000
```复制timeout语法```
timeout = <int>
```复制描述```
query查询超时时间(单位为秒)，默认为600
```复制shortnames语法```
shortnames = <bool>
```复制描述```
是否只显示名称，如果为false则会拼上字段的类型，默认为true
```复制
- params语法```
<string>[,<string>]*
```复制描述```
用于存储过程或者query中替换的变量值
```复制
|  | dbxquery命令每个batch的最大条数的上限默认为10000条，对应配置项为dbxquery.max_fetch_size |
| --- | --- |
Example 19. 示例1
搜索connection配置为179test的数据源对应的test表中的所有数据
```
| dbxquery connection="179test" query="select * from test"
```
复制
### 6.17. dedup
摘要：
```
该命令可以对搜索结果中指定字段值的重复情况进行去重和过滤
```
复制
语法：
```
dedup [<dedup-count>] <field-list> [<dedup-param>]*
```
复制
必要参数：
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
一列字段名称，表明要对结果中的哪些字段进行dedup操作和判定
```复制
可选参数：
- dedup-count语法```
<int>
```复制描述```
此参数指定保留前N条重复出现的日志或结果 默认值：1，默认只保留重复出现的第一条日志
```复制
- dedup-param语法```
<keepevents = <bool>> | <keepempty = <bool>>
```复制描述```
keepevents:是否保留重复事件,keepempty:是否保留空事件
```复制参数keepevents语法```
<bool>
```复制描述```
若为true，则会保留所有重复出现的日志，但会移除重复值（除去第一条出现的日志） 默认值：false，重复出现的日志将会被整体移除
```复制keepempty语法```
<bool>
```复制描述```
若为true，则会保留指定field name的值为空的日志 默认值：false，若指定的一个或多个field name值为空，那么该条日志将会被移除
```复制
Example 20. 示例1
列出每个城市不同的apache.status的各前三条结果
```
* | table apache.status, apache.geo.city | dedup 3 apache.status, apache.geo.city
```
复制
### 6.18. delete
摘要：
```
该命令可以对搜索结果中query部分命中的原始日志进行删除
```
复制
语法：
```
delete
```
复制
|  | delete仅对query命中的原始日志部分进行删除，且删除有一定延迟 |
| --- | --- |
Example 21. 示例
列出tag为lytest中的原始日志
```
tag:lytest | delete
```
复制
### 6.19. download
摘要：
```
该命令可以download命令之前产生的结果下载到外部文件
```
复制
语法：
```
download <filename> [<param-options>]*
```
复制
必要参数：
- filename语法```
filename = <string>
```复制描述```
指定下载文件的名称，无须带后缀
```复制
可选参数：
- param-options语法```
<fileformat> | <maxsize> | <maxevents> | <charset> | <format> | <compress>
```复制描述```
null
```复制参数fileformat语法```
fileformat = <string>
```复制描述```
必要参数。文件格式类型，可选[csv, json, txt, xlsx]，默认为"txt"
```复制maxsize语法```
maxsize=<string>
```复制描述```
下载的最大文件大小，其值为整数，支持单位[g, m, k, b]，默认值见配置项 download.max_file_size
```复制maxevents语法```
maxevents=<string>
```复制描述```
下载的最大事件数，默认值见配置项 download.max_events
```复制charset语法```
charset = <string>
```复制描述```
字符集，可选[UTF-8, GBK]，默认为"UTF-8"
```复制format语法```
format = <string>
```复制描述```
csv 文件的格式，可选`rfc`,`default`, 默认为`default`
```复制compress语法```
compress = <bool>
```复制描述```
使用该选项控制下载文件是否压缩, 默认值是 false
```复制
Example 22. 示例1
将原始日志中仅保留appname和hostname两个字段的结果下载为aatest.json的结果文件
```
* | table appname, hostname | download filename="aatest" fileformat="json"
```
复制
### 6.20. esma
摘要：
```
该命令可以对某一个字段的未来值进行预测
```
复制
语法：
```
esma <field> [<as-field-clause>] <param-options>*
```
复制
必要参数：
- field语法```
string
```复制描述```
用于表示进行预测的字段
```复制
可选参数：
- as-field-clause语法```
as <field> | <single-quoted-string>
```复制描述```
表示将预测结果字段重新命名，默认为 _predict_<field>
```复制
- param-options语法```
<timefield> | <period> | <futurecount>
```复制描述```
参数选项
```复制参数timefield语法```
timefield = <field>
```复制描述```
时间参数字段。
```复制period语法```
period = <int>
```复制描述```
表示数据中的时间周期长度，如果没有指定，我们将自己进行计算
```复制futurecount语法```
futurecount = <int>
```复制描述```
表示对未来进行预测的个数，默认为5，最大值为100
```复制
|  | esma命令需要用在统计命令后面，同时统计命令需要根据时间进行分组，并且esma 的timefield字段需要指定为该时间分组字段 |
| --- | --- |
Example 23. 示例1
统计过去一年的每天的平均延迟（我们将周期设置为7天），从而推测接下来一个月的网络延迟
```
* | bucket timestamp span=1d as ts | stats avg(network.latency) as latency by ts | esma latency timefield=ts period=7 futurecount=30
```
复制
### 6.21. eval
摘要：
```
计算表达式并将生成的值放入到新的字段中
```
复制
语法：
```
eval <field>=<expression> [, <field>=<expression>]*
```
复制
必要参数：
- field语法```
<field>|<single-quoted-string>
```复制描述```
生成的目标字段名称，如果字段已存在字段的值将被覆盖。
```复制
- expression语法```
<string> | <field> | <operator> | <expression_function>
```复制描述```
代表目标字段值的值、变量、运算符以及函数的组合。
```复制
可选参数：
- expression_function描述```
spl本身已经支持了部分函数，请参看eval函数
```复制
- operator描述```
运算符按照优先级自低到高排序:
1. ||（逻辑或）二元操作符，操作数必须是布尔类型
2. &&（逻辑与）二元操作符，操作数必须是布尔类型
3. !=（不等于）==（等于）
4. >=，>，<=, <
5. +，- 算术加减，支持数值类型，+另支持字符串
6. *，/，% 算术乘，除，余，乘除支持数值类型
```复制
Example 24. 示例1
对于web日志，将根据响应时间获取short, middle, long三个分类值
```
logtype:apache | eval length=case(apache.resp_len < 1500, "short", apache.resp_len > 2000, "long", default, "middle")
```
复制
Example 25. 示例2
对创建出的一条数据添加tag和appname字段
```
| makeresults count=1 | eval tag="tag1",appname="app1"
```
复制
### 6.22. eventstats
摘要：
```
提供统计信息，可以选择字段进行分组，并且将按照当前行所属于的分组的统计结果作为新的字段值添加在本行
```
复制
语法：
```
eventstats (<stats-function> [as <field>])+ [by <field-list>]
```
复制
必要参数：
- stats-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | list | values | top | es | dhg | hg | pct | pct_ranks | rb | sparkline | mad
```复制描述```
与stats命令结合的函数，请参考[#与stats有关的函数]
```复制
可选参数：
- field-list语法```
<field>[,<field>]*
```复制描述```
要保留的字段以逗号或者空格分割的字段列表
```复制
|  | eventstats保留的事件数的上限对应的配置项为eventstats.event_size |
| --- | --- |
Example 26. 示例1
搜索所有数据并且按照数据logtype计算count值并且根据logtype给每行添加上count()字段
```
* | eventstats count() by logtype
```
复制
### 6.23. fields
摘要：
```
通过操作符保留或排除结果中的系列字段。
```
复制
语法：
```
fields [<operator>] <field-list>
```
复制
必要参数：
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
要保留或排除的字段以逗号或者空格分割的字段列表，支持通配符
```复制
可选参数:
- operator语法```
+ | -
```复制描述```
+是保留，-是排除，默认为+。
```复制注意：```
对字段列表的操作是一致的，都为保留或都为排除。
```复制默认值：```
+
```复制
Example 27. 示例1
仅保留appname和hostname字段
```
logtype:apache | stats count() by appname,hostname | fields appname, hostname
```
复制
Example 28. 示例2
仅保留以json.e开始的字段
```
* | stats count() by json.activated,json.id,json.excess_action,json.excess_times_limit | fields + json.e*
```
复制
Example 29. 示例3
排除appname和hostname字段
```
* | fields - appname, hostname
```
复制
### 6.24. filldown
摘要：
```
将某些字段的null值用上一个最近的非null值进行填充，支持通配符
```
复制
语法：
```
filldown [<space-or-comma-field-list>]
```
复制
可选参数：
- space-or-comma-field-list语法```
<field>(,<field>)* | <field> <field>*
```复制描述```
要进行填充的字段列表，可用空白或逗号分隔。字段名可使用通配符匹配
```复制
Example 30. 示例：
对所有字段，都进行null值填充
原始数据:
```
* | filldown
```
复制
Example 31. 示例：
对字段x和满足通配符c*条件的字段，进行null值填充
原始数据:
```
* | filldown x c*
```
复制
### 6.25. fillnull
摘要：
```
将空值替换为指定值。空值是在特定结果中缺失但在另一结果中存在的字段值。使用fillnull与字符串替换空字段值
```
复制
语法：
```
fillnull [value=<string>] <field-list>
```
复制
必要参数：
- field-list语法```
<field> (,<field>)*
```复制描述```
用于指定要填充空值的字段
```复制
可选参数：
- value语法```
<string>
```复制描述```
指定一个字符串来替换空值，默认为"0"
```复制
Example 32. 示例1
创建一条日志并且a字段为空，使用fillnull来给a字段填充默认值fillnull_source
```
|makeresults count=1 | eval a=null| fillnull value="fillnull_source" a
```
复制
### 6.26. foreach
摘要：
```
对字段列表执行流式命令
```
复制
语法：
```
foreach <wc-field-list> <foreach-options>* <sub-pipe>
```
复制
必要参数：
- wc-field-list语法```
<wc-field> ( , <wc-field>)*
```复制描述```
字段列表, 支持*作为通配符
```复制
- sub-pipeline语法```
[[ command ( | command)* ]]
```复制描述```
子命令模板，支持管道分隔的多个命令, 必须是流式命令
```复制
可选参数：
- foreach-options语法```
<fieldstr-option> | <matchstr-option> | <matchseg1-option> | <matchseg2-option> | <matchseg3-option>
```复制描述```
foreach可选的参数
```复制参数fieldstr-option语法```
fieldstr=<string>
```复制描述```
匹配的字段名，默认是<<FIELD>>
```复制matchstr-option语法```
matchstr=<string>
```复制描述```
所有通配符匹配到的内容, 默认是<<MATCHSTR>>
```复制matchseg1-option语法```
matchseg1=<string>
```复制描述```
第一个通配符匹配到的内容，默认是<<MATCHSEG1>>
```复制matchseg2-option语法```
matchseg2=<string>
```复制描述```
第二个通配符匹配到的内容，默认是<<MATCHSEG2>>
```复制matchseg3-option语法```
matchseg3=<string>
```复制描述```
第三个通配符匹配到的内容，默认是<<MATCHSEG3>>
```复制
Example 33. 示例1
对所有前缀是count的字段值加1
```
* | foreach count* [[ eval <<FIELD>> = <<FIELD>> + 1 ]]
```
复制
Example 34. 示例2
对所有前缀是count的字段求和
```
* | eval sum = 0 | foreach count* [[ eval tmp = sum | eval sum = tmp + <<FIELD>> ]]
```
复制
### 6.27. fromes
摘要：
```
是一个可以使用elastic dsl来查elasticsearch的数据并作为spl的查询语句的命令
```
复制
语法：
```
fromes <fromes-options>* <index> <querydsl>
```
复制
参数：
- fromes-options语法```
<host> | <port>
```复制描述```
fromes可选的参数
```复制参数host语法```
host=<string>
```复制描述```
指定es服务的ip, 默认值为localhost
```复制port语法```
port=<int>
```复制描述```
指定es服务监听的端口, 默认值为9200
```复制
- index语法```
index=<string>
```复制描述```
指定搜索的索引
```复制
- querydsl语法```
querydsl=<string>
```复制描述```
es支持的dsl json, json内的单引号需要加 \ 转义
```复制
Example 35. 指定host、index, 执行搜索
```
|fromes host=10.200.0.140 index=logs-my_app-default querydsl='{
          "query": {
            "match_all": { }
          }
        }'
```
复制
Example 36. 指定host、port、index, 执行聚合
```
|fromes host=10.200.0.140 port=9200 index=logs-my_app-default querydsl='{
          "query": {
            "match_all": { }
          },
          "aggs": {
            "@timestamp_avg": {
              "avg": {
                "field": "@timestamp"
              }
            }
          }
        }'
```
复制
### 6.28. fromkafkapy
摘要：
```
消费kafka的数据并作为spl的查询语句的命令
```
复制
语法：
```
fromkakfapy (bootstrap-servers | topic | action | partitions | offset | limit | timeout-ms)*
```
复制
参数：
- bootstrap-servers语法```
bootstrap-servers=<string>
```复制描述```
kafka服务列表, 使用逗号分隔。默认值为'localhost:9092'
```复制
- topic语法```
topic=<string>
```复制描述```
指定消费的主题
```复制
- action语法```
action=consume | show-partition-info
```复制描述```
consume是进行消费，show-partition-info是查询分区信息，默认值为为consume.
```复制
- partitions语法```
partitions=<string>
```复制描述```
指定分配分区, 分区不存在时报错, 默认分配所有分区。如 partitions=[0,1]
```复制
- offset语法```
offset=earliest | latest | '0:100, ...'
```复制描述```
分区的偏移量。默认是根据分配分区与指定limit计算偏移量消费，消费最近limit条
```复制earliest指定从分配的分区最早的偏移量开始消费；latest指定从分配的分区最近的偏移量开始消费；'0:100, …​'指定分配的分区与偏移量进行消费, 分区不存在时报错，这种方式不能和partitions同时使用。
- limit语法```
limit=<int>
```复制描述```
消费的条数限制. 当消费到指定的数量时停止消费, 默认值为100
```复制
- timeout-ms语法```
timeout-ms=<int>
```复制描述```
费的超时限制. 当在指定时间内没有收到record时停止消费，默认值为1000
```复制
Example 37. 查看test主题的分区信息
```
|fromkafkapy action=show-partition-info topic=test
```
复制
Example 38. 消费test主题，直到达到3s的超时条件或者获取100条的record
```
|fromkafkapy topic=test timeout-ms=3000
```
复制
Example 39. 从指定分区0，最近的偏移量开始消费
```
|fromkafkapy topic=test partitions=[0] offset=latest
```
复制
Example 40. 从偏移量5开始消费分区0
```
|fromkafkapy topic=test offset='0:5'
```
复制
### 6.29. gentimes
摘要：
```
可以生成指定范围的时间戳数据
```
复制
语法：
```
| gentimes <start> <param-options>*
```
复制
必要参数：
- start语法```
start = <string>
```复制描述```
用于指定开始时间，可选[ "2019-01-01" | "2019-01-01 18:00:00" | "1571557017000" | "-1d/d" | "now-1d" ]
```复制
可选参数：
- param-options语法```
<end> | <increment> | <humantime> | <timezone>
```复制参数end语法```
end = <string>
```复制描述```
用于指定结束时间，可选[ "2019-01-01" | "2019-01-01 18:00:00" | "1571557017000" | "-1d/d" | "now-1d" ]，默认为当天23:59:59
```复制increment语法```
increment = <string>
```复制描述```
用于指定步长，时长+[s|m|h|d], 默认为1d
```复制humantime语法```
humantime = <bool>
```复制描述```
是否生成两个个新字段为starthuman和endhuman，用于将start和end转换为YYYY-MM-dd:hh:mm:ss格式
```复制timezone语法```
timezone = <string>
```复制描述```
用于指定时区，默认为+08:00
```复制
|  | 如果没有end，则start必须小于等于今天若时间范围为3.5d，但是increment为1d，则返回四条结果并且endtime为4d并不是3.5d |
| --- | --- |
Example 41. 示例1
根据2019-01-01~2019-01-04这个时间范围，按步长为1d生成出对应的三条数据，并且根据humantime参数为true，生成出对应的starthuman以及endhuman字段
```
| gentimes start="2019-01-01" end="2019-01-04" increment="1d" humantime=true
```
复制
### 6.30. geostats
摘要：
```
使⽤geostats命令可以基于地理位置信息，即经度和纬度进行分区域统计
```
复制
语法：
```
geostats [<geostats-params>]* <stats-single-value-func> [<stats-single-value-func>]* [by <by-field>]
```
复制
必要参数：
- stats-single-value-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | mad
```复制描述```
与stats命令结合的部分函数，请参考[#与stats有关的函数]
```复制
可选参数：
- geostats-params语法```
[latfield=<field>] [longfield=<field>] [outputlatfield=<field>] [outputlongfield=<field>] [binspanlat=<double>] [binspanlong=<double>] [maxzoomlevel=<int>]
```复制参数latfield语法```
latfield=<field>
```复制描述```
指定的纬度字段，默认值为lat
```复制longfield语法```
longfield=<field>
```复制描述```
指定的经度字段，默认值为lon
```复制outputlatfield语法```
outputlatfield=<field>
```复制描述```
结果中纬度分桶后的字段名，默认值为latitude
```复制outputlongfield语法```
outputlongfield=<field>
```复制描述```
结果中经度分桶后的字段名，默认值为longitude
```复制binspanlat语法```
binspanlat=<double>
```复制描述```
纬度分桶间隔，默认值为22.5
```复制binspanlong语法```
binspanlong=<double>
```复制描述```
经度分桶间隔，默认值为45.0
```复制maxzoomlevel语法```
maxzoomlevel=<int>
```复制描述```
最大缩放级别，最大值为9
```复制
- by-field语法```
<field>
```复制描述```
分组字段，所有的stats_func将在分组内统计
```复制
|  | 由于geostats支持按照多个字段进行分组,所以这里会与stats命令中的by字段有同样的限制，详情见stats命令的NOTE中的group.size以及stats.oneby.group_size配置项 |
| --- | --- |
Example 42. 示例1
纬度字段为verdors.VendorLatitude，经度字段为verdors.VendorLongitude，结果中纬度分桶字段为ccc，结果中经度字段分桶字段为ddd，纬度分桶间隔为35.5，经度分桶间隔为40.65，最大缩放级别为8时对应地理区域中事件数的统计值。
```
appname:vendors | geostats latfield=vendors.VendorLatitude longfield=vendors.VendorLongitude outputlatfield=ccc outputlongfield=ddd binspanlat=35.5 binspanlong=40.65 maxzoomlevel=8 count() as cnt by hostname
```
复制
### 6.31. inputlookup
摘要：
```
使⽤inputlookup 命令可以读取lookup的表，⽬前lookup表⽀持csv⽂件(以.csv为后缀名)，kv字典，资产实体（通过lookup-type参数指定）。csv⽂件第⼀⾏需为字段名的信息。
```
复制
语法：
```
inputlookup <param-options>* <lookup-type>? <filename-or-kvstorename-or-assetname>
```
复制
必要参数：
- filename-or-kvstorename-or-assetname语法```
<file-name>
```复制描述```
文件名必须以.csv结尾，无须提供路径。文件为通过字典上传或者outputlookup写出的文件。kvstore必须在所属domain和app下已经定义好。使用资产实体时资产模型必须存在。
```复制
可选参数：
- lookup-type语法```
(csv: | kvstore: | asset: )
```复制描述```
inputlookup文件类型，csv：csv文件；kvstore：kv字典；asset：资产实体。不填优先匹配csv，不成功匹配为kv字典
```复制
- param-options语法```
<max> | <start> | <format>
```复制描述```
离散化选项
```复制参数max语法```
max = <int>
```复制描述```
最多读取多少个事件，默认值为 10,000,000
```复制start语法```
start = <int>
```复制描述```
指定从第多少个事件(每⾏为⼀个事件)开始读取，NOTE: start值从0开始，如果start=4表⽰第五个事件，默认值为 0
```复制format语法```
format = <string>
```复制描述```
csv 文件的格式，可选`rfc`,`default`, 默认为`default`
```复制
Example 43. 示例1
读取a.csv中的事件信息
```
| inputlookup a.csv
```
复制
Example 44. 示例2
读取kvstore名为packetsrc中的事件信息
```
| inputlookup packetsrc
```
复制
### 6.32. iplocation
摘要：
```
从ip地址抽取地理信息
```
复制
语法：
```
iplocation [prefix=<string>] <field>
```
复制
必要参数：
- field语法```
prefix=<field>
```复制描述```
ip字段
```复制
可选参数：
- prefix语法```
prefix=<string>
```复制描述```
给产生的字段名加上前缀
```复制
Example 45. 示例1
从clientip字段抽取出地理信息
```
* | iplocation clientip
```
复制
### 6.33. join
摘要：
```
对父管道的结果和子管道的结果进行类似sql的join
```
复制
语法：
```
join <param-options>* <field-list> [[ subsearch ]]
```
复制
必要参数：
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
指定要用于连接的具体字段
```复制
- subsearch语法```
<sub_pipeline>
```复制描述```
子搜索管道
```复制
可选参数：
- param-options语法```
<type> | <max> | <overwrite>
```复制描述```
join命令的选项
```复制参数type语法```
type = inner | left
```复制描述```
要执行的连接类型，inner和left的区别局势他们如何对待主管道和自管道中的结果不匹配事件，inner连接的结果将不包括没有匹配的事件，left连接不要求必须具有匹配的字段，对于主管道中不匹配的事件将被保留。默认值是inner
```复制max语法```
max = <int>
```复制描述```
指定每个主结果可以连接的最大自结果数，默认为1
```复制overwrite语法```
overwrite = <bool>
```复制
|  | 由于性能的影响，子管道的结果数最大为50000条，对应配置项join.subsearch.max_count。示例：appname:apache |join type=left timestamp [[*|stats count() by timestamp|fields timestamp]]复制描述：上述语句中join语句内的子查询的最大结果数为50000条，如果超过该数值则将之后的数据丢弃，然后将appname:apache的结果与join的子查询中的子查询的50000条数据进行left join操作。注意：子查询结果数超过50000条时，系统会给出提示"触发配置项group.size的配置上限，数据返回不完整"。复制 |
| --- | --- |
Example 46. 示例
统计过去一天每个小时每个ip的事件数占当前这个小时总数的百分比
```
logtype:apache | bucket timestamp span=1h as ts | stats count() as ip_count by apache.clientip,ts | join type=left ts [[ logtype:apache | bucket timestamp span=1h as ts | stats count() as hour_count by ts ]] | eval ippercent=100 * ip_count / hour_count
```
复制
### 6.34. jpath
摘要：
```
jpath用于支持对json的数据处理，提供类似xpath的机制，并配合上多值函数对json数据进行提取和处理
```
复制
语法：
```
jpath [input=<field>] output=<field> path=<json-path>
```
复制
必要参数：
- output语法```
<field>|<single-quoted-string>
```复制描述```
表示抽取的输出字段名，字段类型收到json-path的影响，可能为单值也可能为多值类型
```复制
- json-path语法```
<double-quoted-string>
```复制描述```
json-path描述的路径。语法详见：https://github.com/json-path/JsonPath
```复制
| 操作符 | 描述 |
| --- | --- |
| * | 通配符，可用于通配子节点或者数组所有元素 |
| .<name> | 名为name的子节点 |
| ['<name>' (, '<name>')] | 方括号形式描述子节点，可以是多个name |
| [<number> (, <number>)] | 方括号形式描述数组的元素，可以是多个number |
| [start:end] | 类似python中的数组用法，表示数据元素的范围 |
Listing 1. json-path示例
```
{
    "store": {
        "book": [
            {
                "category": "reference",
                "author": "Nigel Rees",
                "title": "Sayings of the Century",
                "price": 8.95
            },
            {
                "category": "fiction",
                "author": "Evelyn Waugh",
                "title": "Sword of Honour",
                "price": 12.99
            },
            {
                "category": "fiction",
                "author": "Herman Melville",
                "title": "Moby Dick",
                "isbn": "0-553-21311-3",
                "price": 8.99
            },
            {
                "category": "fiction",
                "author": "J. R. R. Tolkien",
                "title": "The Lord of the Rings",
                "isbn": "0-395-19395-8",
                "price": 22.99
            }
        ],
        "bicycle": {
            "color": "red",
            "price": 19.95
        }
    },
    "expensive": 10
}
```
复制
对应的查询语句结果为:
| Json-path | 描述 |
| --- | --- |
| store.book[*].author | 所有书籍的作者 |
| store.book[2]['author'] | 第三本书的作者 |
| store.book[-2]['price'] | 倒数第二本书的价格 |
| store.book[0,1]['price'] | 第一本和第二本书的价格，类型为多值类型 |
| store.book[1:2]['price'] | 第二本和第三本数的价格，类型为多值类型 |
可选参数：
- input语法```
<field>|<single-quoted-string>
```复制描述```
指定json类型的输入字段，默认为raw_message
```复制
Example 47. 示例
日志原文为{ "a": [  ["x1","r1","31"],  ["x2","r2","32"], ["x3","r3","33"] ]}，其中a为数组的数组，其中第三个元素为价格，抽取所有价格，抽取结果为多值类型
### 6.35. kvextract
摘要：
```
提供抽取功能，从指定字段的字符串值中按照指定的键值分割符和对分隔符进行键值抽取，抽取出来的结果以新字段的形式添加在结果中
```
复制
语法：
```
kvextract [<field>] <kvextract-param>*
```
复制
可选参数：
- field语法```
<field>|<single-quoted-string>
```复制描述```
用于指定抽取的字段，默认为raw_message
```复制
- kvextract-param语法```
<clean_keys> | <kvdelim> | <limit> | <maxchars> | <mv_add> | <pairdelim>
```复制参数clean_keys语法```
clearn_keys = <bool>
```复制描述```
为true时表示当抽取出来的key值中有非字母或数字的字符时，用下划线代替这些字符，默认为false
```复制kvdelim语法```
kvdelim = <string>
```复制描述```
指定键与值的分隔符，默认为'='
```复制limit语法```
limit = <int>
```复制描述```
指定最多抽取多少个键值对，默认为50
```复制maxchars语法```
maxchars = <int>
```复制描述```
指定最多扫描多少个字符用来抽取，默认为10240
```复制mv_add语法```
mv_add = <bool>
```复制描述```
指定是否对同一key抽取时创建多值，默认为false
```复制pairdelim语法```
pairdelim = <string>
```复制描述```
指定kv对的分隔符，默认为' '
```复制
Example 48. 示例1
按照默认参数抽取json.kvex字段
```
appname:lykv | kvextract json.kvex
```
复制
Example 49. 示例2
抽取json.kvex字段，当抽取出来的key值中有非字母或数字的字符时，用下划线代替这些字符
```
appname:lykv | kvextract json.kvex clean_keys=true
```
复制
### 6.36. ldapfetch
摘要：
```
该命令可以将指定dn下属性值返回并添加在每条结果后，dn为前序命令产生的字段名称
```
复制
语法：
```
ldapfetch <ldap-base-param> <dn> [<attrs>]
```
复制
必要参数：
- ldap-base-param语法```
<domain>
```复制描述```
null
```复制
- dn语法```
dn = <field>
```复制描述```
查询ldap的distinguish name，由前序命令产生的字段值替换
```复制
可选参数：
- domain语法```
domain = <string>
```复制描述```
规定连接的ldap配置名称
```复制
- attrs语法```
attrs = <string>
```复制描述```
逗号分割的属性名称
```复制
Example 50. 示例
将dn为memberOf中所有值下的cn description属性返回并添加在每条结果后
```
|ldapsearch domain="SPL" search="(objectclass=group)" attrs="memberOf" |mvexpand memberOf |ldapfetch dn=memberOf attrs="cn,description"
```
复制
### 6.37. ldapfilter
摘要：
```
该命令可以将指定search语句中的属性值返回并添加在每条结果后，其中domain和search都可以由前面命令产生的结果值填充
```
复制
语法：
```
ldapfilter <ldap-base-param> <search> <ldap-filter-param>*
```
复制
必要参数：
- ldap-base-param语法```
<domain>
```复制
- search语法```
search = <string>
```复制描述```
查询ldap的search语句
```复制
可选参数：
- domain语法```
domain = <string>
```复制描述```
规定连接的ldap配置名称
```复制
- basedn语法```
basedn = <string>
```复制描述```
指定搜索开始的ldap节点
```复制
- attrs语法```
attrs = <string>
```复制描述```
为逗号分割的属性名称
```复制
- ldap-filter-param语法```
<basedn> | <attrs>
```复制
Example 51. 示例
将domain为dest_nt_domain字段中所有值并且搜索对应的src_user的结果，取telephoneNumber和displayName字段返回
```
* | |stats count by src_user,dest_nt_domain |ldapfilter domain="$dest_nt_domain$" search="(objectClass=$src_user$)" attrs="telephoneNumber,displayName"
```
复制
### 6.38. ldapgroup
摘要：
```
该命令可以查询规定dn下所有关联的节点信息，结果将增加member_dn member_domain member_name member_type mv_combo五个字段，其中最后一个字段为前四个字段的拼接值
```
复制
语法：
```
ldapgroup <ldap-base-param> [<groupdn>]
```
复制
必要参数：
- ldap-base-param语法```
<domain>
```复制描述```
null
```复制
- groupdn语法```
groupdn = <string>
```复制描述```
查询的dn名称
```复制
可选参数：
- domain语法```
domain = <string>
```复制描述```
规定连接的ldap配置名称
```复制
Example 52. 示例
将名称为spl的ldap配置环境中，dn名称为groupa下所有关联的节点信息
```
|ldapsearch domain="SPL" search="(objectClass=group)"|ldapgroup domain="SPL" groupdn="groupa"
```
复制
### 6.39. ldapsearch
摘要：
```
该命令可以对ldap进行搜索并将指定结果返回
```
复制
语法：
```
ldapsearch <ldap-base-param> <search> <ldap-search-param>*
```
复制
必要参数：
- ldap-base-param语法```
<domain>
```复制
- search语法```
search = <string>
```复制描述```
查询ldap的search语句
```复制
可选参数：
- attrs语法```
attrs = <string>
```复制描述```
为逗号分割的属性名称
```复制
- domain语法```
domain = <string>
```复制描述```
规定连接的ldap配置名称
```复制
- scope语法```
scope = base | noe | sub
```复制描述```
代表抽哪一层的结果, `base`代表只搜索当前层级、`noe`代表当前层级+向下一级，`sub`代表所有子层级的结果都抽取
```复制
- limit语法```
limit = <int>
```复制描述```
规定返回结果最多有多少条
```复制
- basedn语法```
basedn = <string>
```复制描述```
指定搜索开始的ldap节点
```复制
- ldap-search-param语法```
<basedn> | <attrs> | <limit> | <scope>
```复制
Example 53. 示例
查询ldap配置为SPL环境中所有objectclass为user的节点
```
| ldapsearch domain="SPL" search="(objectClass=user)"
```
复制
### 6.40. ldaptestconnection
摘要：
```
该命令可以测试连接已配置好的ldap环境
```
复制
语法：
```
ldaptestconnection <ldap-base-param>
```
复制
可选参数：
- ldap-base-param语法```
<domain>
```复制
- domain语法```
domain = <string>
```复制描述```
规定连接的ldap配置名称
```复制
Example 54. 示例
测试连接ldap配置名称为testcon的ldap环境配置，如成功返回true
```
| ldaptestconnection domain="testcon"
```
复制
### 6.41. limit
摘要：
```
以搜索顺序，返回前N个结果或者直到eval表达式为false的结果。使用与head相同
```
复制
语法：
```
limit [limit-expr]
```
复制
可选参数：
- limit-expr语法```
<number> | (<expression>) [limit-params]*
```复制描述```
返回结果数或要满足的表达式
```复制参数number语法```
<int>
```复制描述```
返回结果的数量。默认是10
```复制expression语法```
<bool>
```复制描述```
有效的eval表达式，其值为布尔值。搜索将返回结果，直到该表达式的计算结果为false
```复制limit-params语法```
<null = <bool>> | <keeplast = <bool>>
```复制描述```
控制参数
```复制参数null语法```
null=<bool>
```复制描述```
控制eval表达式评估为NULL时如何处理，设置为true则认定eval表达式为true，为false则认定eval表达式为false。默认为false
```复制keeplast语法```
keeplast=<bool>
```复制描述```
控制是否保留结果集中最后一个使得eval表达式评估为false的结果，设置为true则保留，为false则丢弃。默认为false
```复制
Example 55. 示例1
保留前2条结果
```
sourcetype:splserver | limit 2
```
复制
Example 56. 示例2
当count字段为null时，使得count<5评估为NULL，认定count<5为true，保留直到使得count<5为false的结果，并且保留最后一条
```
sourcetype:splserver | limit count<5 null=true keeplast=true
```
复制
### 6.42. head
摘要：
```
以搜索顺序，返回前N个结果或者直到eval表达式为false的结果。使用与limit相同
```
复制
语法：
```
head [limit-expr]
```
复制
可选参数：
- limit-expr语法```
<number> | (<expression>) [limit-params]*
```复制描述```
返回结果数或要满足的表达式
```复制参数number语法```
<int>
```复制描述```
返回结果的数量。默认是10
```复制expression语法```
<bool>
```复制描述```
有效的eval表达式，其值为布尔值。搜索将返回结果，直到该表达式的计算结果为false
```复制limit-params语法```
<int>
```复制描述```
控制参数
```复制参数keeplast语法```
keeplast=<bool>
```复制描述```
控制是否保留结果集中最后一个使得eval表达式评估为false的结果，设置为true则保留，为false则丢弃。默认为false
```复制null语法```
null=<bool>
```复制描述```
控制eval表达式评估为NULL时如何处理，设置为true则认定eval表达式为true，为false则认定eval表达式为false。默认为false
```复制
Example 57. 示例1
保留前2条结果
```
sourcetype:splserver | head 2
```
复制
Example 58. 示例2
当count字段为null时，使得count<5评估为NULL，认定count<5为true，保留直到使得count<5为false的结果，并且保留最后一条
```
sourcetype:splserver | head count<5 null=true keeplast=true
```
复制
### 6.43. lookup
摘要：
```
使用lookup命令可以将外部文件中的结果和当前管道的结果进行join，可为/data/rizhiyi/spldata/lookup下的本地文件、outputlookup生成的文件或kvstore存储或资产实体。
```
复制
语法：
```
lookup <lookup-field-list> <lookup-type>? <filename-or-kvstorename-or-assetname> on <join-field-list> <param-options>*
```
复制
必要参数：
- lookup-field-list语法```
<lookup-field> (, <lookup-field>)*
```复制描述```
外部文件中需要加入搜索结果的字段列表
```复制参数lookup-field语法```
<field> [as <field>]
```复制描述```
对字段列表的重命名
```复制
- filename-or-kvstorename-or-assetname语法```
<file-name>
```复制描述```
需要关联的外部文件的uri地址，支持http和https地址，或者本地共享文件的地址，或者已经定义并创建好的kvstore名称，或者已经存在的资产模型名称
```复制
- join-field-list语法```
<join-field> (, <join-field>)*
```复制描述```
join字段列表
```复制参数join-field语法```
<field> = <field>
```复制描述```
等号左边的field表示主结果中的字段，等号右边的field为外部文件中的字段
```复制
可选参数：
- lookup-type语法```
(csv: | kvstore: | asset: )
```复制描述```
lookup文件类型，csv：csv文件；kvstore：kv字典；asset：资产实体。不填优先匹配csv，不成功匹配为kv字典
```复制
- param-options语法```
<case-sensitive-match> ｜ <match-type> | <format>
```复制描述```
null
```复制参数max语法```
max = <int>
```复制描述```
指定每个主结果可以连接的最大自结果数，默认为1
```复制overwrite语法```
overwrite = <bool>
```复制描述```
是否覆盖主结果，默认为false
```复制case-sensitive-match语法```
case_sensitive_match = <bool>
```复制描述```
精确匹配时是否区分大小写，默认值为true
```复制match-type语法```
match_type = <match-type-funcs> (, <match-type-funcs>)*
```复制描述```
lookup的匹配方式，目前支持cidr和wildcard，默认为精确匹配(不需要单独写出)。这里field-list填写的是搜索数据中所使用该规则的字段列表，非csv中需要使用该规则的字段列表。
```复制参数match-type-funcs语法```
cidr(<field>[, <field>]*) | wildcar(<field>[, <field>]*)
```复制描述```
cidr或wildcard的匹配规则
```复制format语法```
format = <string>
```复制描述```
csv 文件的格式，可选`rfc`,`default`, 默认为`default`
```复制
|  | http和https不支持重定向lookup命令所使用的文件默认的大小限制为8m，对应配置项lookup.max_download_size如果文件下载超时为8s，超过该时间即为读取失败并报错，对应配置项lookup.download_timeout如果指定本地文件，为字典管理列表中的文件由于csv的数据字段都是字符串类型，因此注意join的字段的类型应该为字符串类型才可以lookup成功，如果字段不为字符串类型，可使用eval进行转换。 |
| --- | --- |
Example 59. 示例1
假设外部csv文件有以下字段：host, user, department, 将搜索结果中的username字段和csv文件的user进行关联，在搜索结果中增加host, user, department字段
```
| makeresults count=1 | eval username="hunter" | lookup user,host,department /data/rizhiyi/spldata/lookup/user.csv on username=user
```
复制
Example 60. 示例2
假设外部csv文件有以下字段：id,mask,pattern,raw, 将搜索结果中的id字段和csv文件的id进行精确匹配，搜索结果中的ip和csv中的mask进行cidr匹配，搜索结果中的rvalue与csv中的pattern进行通配匹配，在搜索结果中增加mask,pattern,raw字段
```
appname:a | rename 'value' as rvalue | lookup mask,pattern,raw lookupJoiner.csv on id=id,ip=mask,rvalue=pattern match_type=cidr(ip),wildcard(rvalue)
```
复制
lookupJoiner.csv内容
"id","mask","pattern","raw"
"1","192.168.1.126/24","abc*","one"
"2","192.168.4.138/24","cd*","two"
"3","aaaaaaaa","abc*","three"
"4","192.168.1.126/24","cd","four"
"5","192.168.1.126/24","ef*","five"root@192.168.1.141:/data/rizhiyi/spldata/lookup
关联结果：
Example 61. 示例3
假设外部csv文件有以下字段：appname,word, 将搜索结果中的app字段和csv文件的appname进行关联，在搜索结果中增加word字段，其中匹配时不区分大小写。
```
| makeresults | eval app = "Test" | lookup word match_test.csv on app=appname case_sensitive_match=false
```
复制
### 6.44. lookup2
摘要：
```
使用lookup2命令可以添加自定义字段。通过在指定脚本存放路径下(默认为：/data/rizhiyi/spldata/lookup/script)添加相关的配置文件以及python处理数据文件即可添加自定义字段。
```
复制
语法：
```
lookup2 <script-name> <param-options>*
```
复制
必要参数：
- script-name语法```
<identifier>
```复制描述```
需要关联的script-name
```复制
可选参数：
- param-options语法```
<outputfields>
```复制参数outputfields语法```
outputfields <field>(,<field>)*
```复制描述```
结果过滤字段，结果中只包含指定的字段
```复制
配置文件以及python文件描述：
- 配置文件：文件名：```
lookup_external.cfg(必须为该名称，否则将读取不到配置)
```复制文件内容：示例配置文件：```
lookup_script_names = ["external_script"]
// lookup_scripts config
lookup_scripts {
    external_script {
        external_file = "external_script.py"
        input_fields = "appname,tag"
        join_fields = "appname,tag"
        output_fields = "appname,tag,appnametag"
  }
}
```复制说明：lookup_script_names：用于指定当前所有的python脚本名称lookup_scripts：用于写入每个script-name的配置信息external_script：代表script-name的名称，即为lookup2之后使用的script-name名称，内部是该脚本对应的相关配置信息external_file：用于指定该script-name对应的python文件名称input_fields：用于指定该python文件的输入字段(输入字段顺序严格按照该顺序输入数据)join_fields：用于指定该python文件输出结果与上一个命令的结果进行join时所使用的字段output_fields：用于指定该python文件输出字段(需严格保证输出字段顺序),可以通过冒号(:)分隔符来指定输出字段类型，如：timestamp:long等，目前支持的类型有 long,double,boolean,默认为字符串。
- Python脚本：文件名：```
需要与配置文件中external_file的名称保持一致
```复制文件内容：```
将输入的数据经过处理之后生成新的数据并且返回。
```复制协议：```
无头的csv协议。输入以及输出严格按照配置文件的输入输出顺序
```复制示例：```
#!/usr/bin/env python
import csv
import sys
def main():
    infile = sys.stdin
    outfile = sys.stdout
    r = csv.reader(infile)
    w = csv.writer(outfile)
    for result in r:
        if result:
            result.append(result[0]+result[1])
            w.writerow(result)
main()
```复制
|  | lookup2的脚本默认存放路径为：/data/rizhiyi/spldata/lookup/script，对应的配置项为lookup2.script_path，如果需要修改脚本存放路径则修改该配置项即可。如果为多台spl集群则需要每台机器上都需要上传配置文件以及python脚本。python文件需要保证在处理同样的join fields的情况下输出统一的output fieldsjoin fields可以支持类型不同进行关联操作，如果在使用lookup2命令之前的数据类型是int，但是python返回的数据类型为string时，是可以关联成功并且返回结果的。 |
| --- | --- |
Example 62. 示例
```
* | lookup2 external_script outputfields appname,timestamp,appnametimestamp
```
复制
该脚本传入appname以及timestamp两个字段值，将起组合的值拼接起来并生成一个新的字段为appnametimestamp。该脚本在配置文件中配置的对应访问名称为external_sccript。
配置文件为：
Listing 2. lookup_external.cfg
```
    lookup_script_names = ["external_script"]
    // lookup_scripts config
    lookup_scripts {
        external_script {
            external_file = "external_script.py"
            input_fields = "appname,timestamp"
            join_fields = "appname,timestamp"
            output_fields = "appname,timestamp,appnametimestamp"
        }
    }
```
复制
python文件为：
Listing 3. external_script.py
```
#!/usr/bin/env python
import csv
import sys
def main():
    infile = sys.stdin
    outfile = sys.stdout
    r = csv.reader(infile)
    w = csv.writer(outfile)
    for result in r:
        if result:
            result.append(result[0]+result[1])
            w.writerow(result)
main()
```
复制
### 6.45. makecontinuous
摘要：
```
在一定数值或时间范围内，根据给定的区间大小，对原始数据升序处理，并补充不连续的区间，区间的划分采用向前圆整的方式。
```
复制
语法：
```
makecontinuous [<field>] <param-options>*
```
复制
可选参数:
- <field>描述：```
需要进行区间补全的字段
```复制默认值：```
timestamp（内置字段）
```复制
- <param-options>语法```
[<span>] | [<start>] | [<end>]
```复制参数：span:描述：```
桶的大小, 可以是数值类型(比如 10)，也可以是时间类型(比如 10d)，单位可以是 s | m | h | d | w | M（更多扩展写法详见小节'与搜索结合使用的修饰符')
```复制默认值：```
1 （如果是时间类型，则表示1ms）
```复制start:描述：```
区间补全的起始范围, 实际的起始范围是start的向前圆整
（时间类型只支持long类型的时间戳）
```复制默认值：```
数据最小值
```复制end:描述：```
区间补全的结束范围, 实际的结束范围是end的向前圆整
（时间类型只支持long类型的时间戳）
```复制默认值：```
数据最大值
```复制
Example 63. 示例：
对数值类型的数据，对字段x，按大小为3进行排序分桶，在216到226之间进行补全
原始数据:
```
* | makecontinuous x span=3 start=216 end=226
```
复制
Example 64. 示例：
对时间类型的数据，对字段time，按大小为1d进行排序分桶和补全
原始数据:
```
* | makecontinuous time span=1d
```
复制
### 6.46. makeresults
摘要：
```
构造指定的结果
```
复制
语法：
```
| makeresults [count=<int>]
```
复制
可选参数：
- count语法```
<int>
```复制描述=     产⽣的结果个数
Example 65. 示例1
产⽣⼀条结果并⽣成新的app字段，⽤于后续map命令
```
| makeresults count = 1 | eval app = "zookeeper" | map "* appname:$app$"
```
复制
### 6.47. map
摘要：
```
该命令可以将上次搜索结果应用于接下来的搜索中， 类似于python的map功能
```
复制
语法：
```
map "<subsearch_command>" [maxsearches = <int>]
```
复制
必要参数：
- <subsearch_command >描述：```
子查询搜索语句 如 `... | map "index = yotta  starttime=$start$ login_name=$user$"`
```复制
可选参数:
- <maxsearches>: 可选参数语法：```
maxsearches = <int>
```复制描述：```
最大的搜索个数
```复制默认：```
10
```复制
|  | 由于性能的考虑，所以对map前一结果的条数限制默认为20，对应的配置项为map.max_searches_limit示例：| stats count() by logtype | limit 2 | rename logtype as type | map "logtype:$type$"描述：上述在map命令之前的数据条数必须小于20条，超出部分将被丢弃复制map命令是否使用cache，使用cache可以加快速度但是同时会增加内存的使用，默认不使用cache，对应的配置项为map.use_cache |
| --- | --- |
Example 66. 示例
列出日志数最多的三种logtype他们各自最大的日志文本长度
```
* |  stats count() by logtype | limit 3 | rename logtype as type | map "logtype:$type$ | stats max(raw_message_length)"
```
复制
以上语句, 实际是先执行
`* |  stats count() by logtype | limit 3 | rename logtype as type`
找出 日志数最大的3个logtype:
可以看到分别为apache,java,和other。
接下来map会对这三个结果分别生成对应的搜索语句
- `logtype:apache | stats max(raw_message_length)`
- `logtype:java | stats max(raw_message_length)`
- `logtype:other | stats max(raw_message_length)`
分别请求搜索，最终将结果进行合并
### 6.48. movingavg
摘要：
```
在一个指定大小的移动窗口下计算某个数值字段的移动平均值
```
复制
语法：
```
movingavg <field>[,window] [as <as_field>] [by <by-field-list>]
```
复制
必要参数：
- field语法```
<field>|<single-quoted-string>
```复制描述```
需要计算移动平均值的字段
```复制
可选参数：
- as-field语法```
<field>
```复制描述```
移动平均值的输出字段名，默认为_moving_avg
```复制
- window语法```
<int>
```复制描述```
移动窗口的大小，对于序号小于window的事件，将根据前面实际的事件进行计算
```复制
- by-field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
分组字段，在分组内进行移动平均值的计算
```复制
Example 67. 示例1
以分钟为单位统计apache返回的apache.resp_len的长度的和，以5为窗口计算移动平均值。得到一个每分钟的响应长度和的平滑后的值
```
logtype:apache | bucket timestamp span=1m as ts | stats sum(apache.resp_len) as sum_len by ts | movingavg sum_len,5 as moving_avg_resp_len
```
复制
### 6.49. mvcombine
摘要：
```
将除指定字段外，其他字段值均相等的行合并为一行，指定字段将合并为一个数组值
```
复制
语法：
```
mvcombine [<sep>] <field>
```
复制
必要参数：
- field语法```
string
```复制描述```
需要指定的字段
```复制
可选参数：
- sep语法```
sep = <string>
```复制描述```
多行合并时的指定字段值作为字符串合并时的分隔符，默认为空格
```复制
|  | mvcombine指令由于需要将相同的行进行合并，所以需要在内存中暂存结果，所以对性能有限制。目前默认限制只对5万条结果进行mvcombine，可以根据自己服务器的性能进行调整spl配置项mvcombine.max_eventsmvcombine需要有除指定field以外值都相同的列 |
| --- | --- |
Example 68. 示例1
```
* | table appname, hostname, ip | limit 10 | mvcombine ip
```
复制
### 6.50. mvexpand
摘要：
```
将一行变成多行，指定字段如果为数组值那么就分成一行一个的值，如果为单值则无影响，其他字段的值原样复制
```
复制
语法：
```
mvexpand <multi-value-field> <param-options>*
```
复制
必要参数：
- multi-value-field语法```
<field>
```复制描述```
须为多值字段，如果字段值为单值将不会有任何改变
```复制
可选参数：
- param-options语法```
<limit>
```复制描述```
null
```复制参数limit语法```
limit = <int>
```复制描述```
一行分裂为多行时取指定字段数组值的前N个进行分裂，因为有可能存在一个数组里面元素过多的情况，所以在此进行限制。
```复制
Example 69. 示例
拆分前的事件:
```
* | mvexpand json.a
```
复制
拆分后
### 6.51. outputlookup
摘要：
```
使用 outputlookup 命令可以生成字典管理中的 csv 文件；也可以生成kvstore或资产实体，名称和类型在命令中指定
```
复制
语法：
```
outputlookup <param-options>* <lookup-type>? <filename-or-kvstorename-or-assetname>
```
复制
必要参数：
- filename-or-kvstorename-or-assetname语法```
<file-name> | <kvstorename> | <asset-name>
```复制描述```
文件名必须以.csv结尾，无须提供路径。文件为通过字典上传或者outputlookup写出的文件。kvstore必须在所属domain和app下已经定义好。使用资产实体时资产模型必须存在。
```复制
可选参数：
- lookup-type语法```
(csv: | kvstore: | asset: )
```复制描述```
outputlookup文件类型，csv：csv文件；kvstore：kv字典；asset：资产实体。不填优先匹配csv，不成功匹配为kv字典
```复制
- param-options语法```
<appendwrite> | <createempty> | <overrideifempty> | <maxresult> | <keyfield> | <format>
```复制描述```
离散化选项
```复制参数appendwrite语法```
appendwrite=<bool>
```复制描述```
表示是否为追加写，默认为false
```复制createempty语法```
createempty=<bool>
```复制描述```
表示如果结果为空是否要创建一个空文件，默认为false
```复制overrideifempty语法```
overrideifempty=<bool>
```复制描述```
表示如果结果为空,是否要用空文件覆盖已经存在的重名文件，默认为true
```复制maxresult语法```
maxresult=<int>
```复制描述```
表示导出结果的最大数量，默认为500000
```复制keyfield语法```
keyfield=<field>
```复制描述```
kvstore中的key字段名称。kvstore中将被指定为arangodb的key值的字段名称
```复制format语法```
format = <string>
```复制描述```
csv 文件的格式，可选`rfc`,`default`, 默认为`default`
```复制
|  | maxresult参数值的最大上限值为500000，如果语句中maxresult参数值超过该值，则取该值作为导出结果的最大数量，对应的配置项为outputlookup.max_result_limit |
| --- | --- |
Example 70. 示例1
将按照时间分组统计的日志个数统计结果写出到外部csv
```
 * | stats count() by timestamp| outputlookup stats_count_by_timestamp.csv
```
复制
命令执行：
下载路径文件：
Example 71. 示例2
将按照clientip、type分组统计的日志个数统计结果写出到kvstore存储
```
index=packet * | stats count() as cnt by json.client_ip, json.type | rename json.client_ip as client_ip | rename json.type as type | outputlookup packetsrc
```
复制
命令执行：
kvstore存储预览：
### 6.52. parse
摘要：
```
用于搜索时动态抽取字段
```
复制
语法：
```
parse [field=<field>] “<regex>” [max_match=<int>]
```
复制
必要参数：
- <regex>语法：```
<正则表达式>
```复制描述：```
支持java的正则表达式，应该包括(?<name>X)形式的named-capturing group, 否则该正则表达式将被忽略
```复制
可选参数：
- <field>语法：```
<string>
```复制描述：```
用于抽取正则表达式的字段，如果未指定，默认为: raw_message
```复制
- <max_match>语法：```
<int>
```复制描述：```
用于指定抽取正则表达式的次数，如果未指定则默认抽取第一个匹配到的值，如果该值大于1则返回类型为多值字段类型，反之返回单值字段类型
```复制
|  | 不支持eval后的字段parse.max_match：max_match参数的上限，用于限制输入指定的max_match参数值，如果超过该配置项的值，默认值为100 |
| --- | --- |
|  | 不支持eval后的字段 |
| --- | --- |
Example 72. 示例1
从日志原文中抽取ip地址，得到新的字段ip_addr,并且按照ip_addr分组并计算appname的个数
```
* | parse "(?<ip_addr>\d+\.\d+\.\d+\.\d+)" | stats count(appname) by ip_addr
```
复制
从结果图中可以看到新生成的ip_addr字段，该字段的格式满足指定的正则表达式
Example 73. 示例2
抽取request_path 的第一级目录outer_path,并按照outer_path分组统计appname的个数
```
logtype:apache | parse field=apache.request_path "^(?<outer_path>/[^/]*)" | stats count(appname) by outer_path
```
复制
Example 74. 示例3
从日志原文中抽取raw_message中的前两组数字
```
*|parse "(?<messageNum>\d+)" max_match=2
```
复制
从结果图中可以看到新生成的messageNum字段，该字段为包含两个值的多值字段
### 6.53. partition
摘要：
```
使用partition命令可以将制定统计搜索中的分组字段的值进行随机分组，以解决离散值过多引起的统计分组数限制的问题
```
复制
语法：
```
partition [<int>] [by <field>] [[ sub_stats_command ]]
```
复制
必要参数：
- <int>格式：```
一个大于0的整数
```复制描述：```
指定将分组字段分成多少组
```复制
- <field>语法：```
string
```复制描述：```
指定后面统计中使用的分组字段名称
```复制NOTE：```
此处指定的分组字段必须为后续统计命令中使用的第一个分组字段
```复制
- <sub_stats_command>描述：```
子搜索命令，必须为统计类型
```复制NOTE：```
此处只可以指定一个统计命令，且必须有分组字段，第一个分组字段和外层by field需要一致。
统计命令包括：stats top sort timechart chart geostats
```复制
Example 75. 示例1
按appname分组统计上周日志个数
```
* | partition 10 by appname [[stats count() by appname]]
```
复制
```
* |stats count() by appname
```
复制
### 6.54. rare
摘要：
```
获取字段出现次数最少的值的集合
```
复制
语法：
```
rare <field> <rare-option>* [by-fieldlist-clause]
```
复制
必要参数：
- field语法```
<field>
```复制描述```
需要rare的字段名
```复制
可选参数：
- rare-option语法```
countfield=<field> | percentfield=<field> | showcount=<bool> | showperc=<bool> | limit=<int> | maxdoc=<int>
```复制描述```
rare选项
```复制参数precision语法```
precision=<number>
```复制描述countfield语法```
countfield=<field>
```复制描述```
rare字段数量输出的字段名, 默认值是'count
```复制percentfield语法```
percentfield=<field>
```复制描述```
rare字段数量百分比输出的字段名, 默认值是'percent'
```复制showcount语法```
showcount=<bool>
```复制描述```
是否输出字段数量, 默认值是true
```复制showperc语法```
showperc=<bool>
```复制描述```
是否输出数量百分比字段, 默认值是true
```复制limit语法```
limit=<int>
```复制描述```
结果的最大行数, 不设置使用spl配置项stats.rare.count_limit
```复制maxdoc语法```
maxdoc=<int>
```复制描述```
限制字段的最大数量，超过的值不会显示，默认不限制
```复制
- by-fieldlist-clause语法```
by <field>(,<field>)*
```复制描述```
分组的字段列表，表示先按照field-list分组，在分组内部计算rare
```复制
Example 76. 示例1
返回出现次数最少出现的，并且在5次以下的srcip，并输出srcip_cnt字段作为count值，srcip_perc段作为百分比
```
  * | rare srcip countfield=srcip_cnt percentfield=srcip_perc maxdoc=5
```
复制
Example 77. 示例2
按照appname进行分组，分组内找到出现次数最少的clientip
```
  * | rare apache.clientip by appname
```
复制
### 6.55. rename
摘要：
```
重新命名指定字段 将src-field的字段，重命名为dest-field，可用于结果集中字段名的修改，比如输出为中文字段名；同时目前支持对多个字段同时进行重命名操作,支持通配符
```
复制
语法：
```
rename <rename-item> [,<rename-item>]*
```
复制
必要参数：
- rename-item语法```
<src-field> as <dest-field>
```复制描述```
需要rename的字段项
```复制参数src-field语法```
<field>|<single-quoted-string>|<wildcardfield>
```复制描述```
需要被重命名的字段
```复制dest-field语法```
<field>|<single-quoted-string>|<wildcardfield>
```复制描述```
dest-field可以是一个合法的字段名，也可以是一个字符串的常量，比如 "Status from apache"
```复制
Example 78. 示例1
将username字段命名为 "用户名"
```
logtype:apache | rename apache.clientip as "ip地址"
```
复制
从结果图中的红色标注中，可以看到apache.clientip字段被重新命名成了ip地址 字段
Example 79. 示例2
将stats生成的cnt字段重命名为计数
```
logtype:apache |  stats count() as cnt by apache.clientip | rename cnt as "计数"
```
复制
Example 80. 示例3
将stats生成的tag字段和sp字段重命名其他名称
```
*  | stats sparkline(avg(apache.resp_len), 1h) as sp by tag | rename tag as tag2, sp as sp2
```
复制
Example 81. 示例4
将stats生成的以json开始的字段重命名为以rejson开始的字段名
```
* |stats count() by json.ip,json.logid,appname|rename json* as rejson*
```
复制
### 6.56. rollingstd
摘要：
```
计算移动标准差
```
复制
语法：
```
rollingstd <field>[,<window>] [as <as-field>] [by <by-field-list>]
```
复制
必要参数：
- field语法```
<field>|<single-quoted-string>
```复制描述```
需要计算移动标准差的字段
```复制
可选参数：
- window语法```
<int>
```复制描述```
移动窗口的大小，对于序号小于window的事件，将根据前面实际的事件进行计算
```复制
- as-field语法```
<field>|<single-quoted-string>
```复制描述```
移动标准差的输出字段名，默认为_rolling_std
```复制
- by-field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
分组字段，在分组内进行移动标准差的计算
```复制
Example 82. 示例1
以时间分组算出apache返回的response的长度的和，以10为窗口计算rolling的标准差。以观察resp_len的波动情况。
```
logtype:apache | stats sum(apache.resp_len) as sum_resp_len by timestamp | rollingstd sum_resp_len,10 as resp_len_rolling_std
```
复制
### 6.57. save
摘要：
```
可将搜索的结果保存为文件，目前仅支持csv格式
```
复制
语法：
```
save <param-options>* <output-file>
```
复制
必要参数：
- output-file语法```
<file-name>
```复制描述```
最好指定挂接共享文件系统的目录，否则保存在yotta的某一台服务器上，基于安全的考虑，本地文件的路径必须为/data/rizhiyi/spldata/或者其子目录。
```复制
可选参数：
- param-options语法```
<format>
```复制描述```
离散化选项
```复制参数format语法```
format = <string>
```复制描述```
csv 文件的格式，可选`rfc`,`default`, 默认为`default`
```复制
Example 83. 示例1
按照hostname分组统计clientip个数，并保存的apache_clientip.csv文件
```
*| stats count(apache.clientip) by hostname | save /data/rizhiyi/spldata/apache_clientip.csv
```
复制
从上图可以看到我们将stats结果输出的到对应文件中去，打开该文件可以看到得到的结果
### 6.58. sort
摘要：
```
按照指定的字段对搜索结果进行排序。对于数值类型将按照数值进行排序，对于字符串类型将按照字典序进行排序。
```
复制
语法：
```
sort [<sort-count>] by <sort-item-list>
```
复制
必要参数：
- sort-item-list语法```
<sort-item>(,<sort-item>)*
```复制描述```
列出排序所依据的字段列表
```复制参数sort-item语法```
[(+|-)]<field>
```复制描述```
单个排序的字段，其中+表示升序，-表示降序，默认为降序
```复制
可选参数：
- sort-count语法```
<int>
```复制描述```
需要排序的事件数
```复制
描述：
```
sort命令将按照给定字段列表对结果进行排序，对于数值类型将按照数值进行排序，对于字符串类型将按照字典序进行排序。
如果sort是对事件排序（query之后），则by可以支持多个字段，但不允许对eval的字段进行排序
如果sort是对统计结果进行排序(stats, transaction之后)，则by仅支持一个字段
```
复制
|  | sort的最大条数限制，用于限制输入指定的sort后追加的int参数，如果大于默认200000数则报错，对应配置项为sort.max_size示例：appname:apache | sort 2000 by +timestamp复制描述上述命令中的2000会首先判断是否小于上述的配置项，如果超过则报错，如果不指定则默认sort 200000条数据复制排序默认保留的条数，默认为10000，对应配置项为sort.maintain_size示例：appname:apache | sort 12000 by +timestamp复制描述上述sort命令后的结果如果超过默认值10000条则只取前10000条数据，之后的数据将被丢弃复制 |
| --- | --- |
Example 84. 示例1
对事件结果按照timestamp升序排序
```
logtype:apache | sort by +timestamp
image::/static/images/Image-140318-043724.084.png[]
```
复制
从结果图中，可以看出事件是按照timestamp进行升序排列的
Example 85. 示例2
统计不同appname下，每个ip的数量，并按照ip的数量降序排序
```
logtype:apache | stats count(apache.clientip) as ip_count by appname | sort by -ip_count
```
复制
从结果图中可以看到，ip_count是从大到小，进行的降序排序
### 6.59. stats
摘要：
```
提供统计信息，可以选择按照字段分组
```
复制
语法：
```
stats (<stats_function> [as <field>])+ [by <field-list>]
```
复制
必要参数：
- stats-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | list | values | top | es | dhg | hg | pct | pct_ranks | rb | sparkline | mad
```复制描述```
与stats命令结合的函数，请参考[#与stats有关的函数]
```复制
可选参数：
- field语法```
<field> | <single-quoted-string>
```复制描述```
每个stats_function都可以定义输出字段名，否则对后续的计算不可见
```复制
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
分组字段，所有的stats_func将在分组内统计
```复制
描述：
```
计算数据集的聚合统计信息，与SQL的聚合类似。如果未使用by子句进行调用，将生成一行，表示对整个传入的数据集进行聚合。如果使用by子句，将为by子句的每个非重复值生成一行。
```
复制
|  | 该命令统计或者表格情况下的最大结果数，默认为20000，对应配置项为stats.max_result_count示例：appname:apache复制描述：group.size 配置项：该命令由于支持by多个字段进行分组统计。如果stats统计时by n个字段进行统计，每个字段假设都有100个值，这样在统计时则会产生100^n个分组，这样一来如果by的字段数足够多或该字段的值的种类足够多，则对性能影响很大，所以我们这边设置了group.size配置项用于限制by的每个的字段的最大分组数复制stats.oneby.group_size 配置项该命令由于支持by单个字段进行分组统计时指定单个字段的最大分组数，如果不填则默认取group.size值。复制 |
| --- | --- |
Example 86. 示例1
统计ip和status的组合的事件数量
```
logtype:apache | stats count() by apache.clientip, apache.status
```
复制
结果图中有三栏，第一栏是apache.clientip,说明是先按照apache.clientip分组，对于每个ip组，然后在按照apache.status分组，最后每个status组都会有一个对应的count值
Example 87. 示例2
统计每个访问路径的平均响应长度
```
logtype:apache | stats avg(apache.resp_len) as avg_resp_len by apache.request_path | rename avg_resp_len as "平均响应长度"
```
复制
### 6.60. streamstats
摘要：
```
可以对数据的连续变化进行累积性的统计，并将统计结果以新字段的方式添加在原始数据中
```
复制
语法：
```
streamstats [<streamstats-params>]* <streamstats-func-as> [, <streamstats-func-as> ]* [by <field-list>]
```
复制
必要参数：
- streamstats-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | derivative | exact_dc | sumsq | var | stddev | list | values | distinct | top | rate
```复制描述```
与stats命令结合的部分函数，请参考[#与stats有关的函数]。
```复制
可选参数：
- streamstats-params语法```
[reset_on_change=<bool>] | [reset_before=<eval-expression>] | [reset_after=<eval-expression> ] | [current=<bool>] | [window=<int>] | [time_window=<span-length>] | [global=<bool>] | [allnum=<bool>] | [timefield=<field>]
```复制参数reset-before语法```
reset_before=<eval-expression>
```复制描述```
在生成对某一事件的统计值之前重置统计。当此参数与window一起使用时，window也会被重置。
```复制reset-after语法```
reset_after=<eval-expression>
```复制描述```
在生成对某一事件的统计值之后重置统计。当此参数与window一起使用时，window也会被重置。
```复制time-window语法```
time_window=<span-length>
```复制描述```
时间窗口的大小。当time_window和window一起使用时，time_window规定的是一个window内部的时间窗口大小。无论是window还是time_window其实影响的都是在某一窗口中命中的事件数[使用time_window参数的前提是时间必须是按时间字段排序的]
```复制参数span-length语法```
span_length=<int> <timeunit>
```复制描述```
每个时间窗口的跨度，第一个数字为系数
```复制参数timeunit语法```
timeunit=s | m | h | d | w
```复制描述```
时间单位，分别表示秒，分钟，小时，天，周
```复制reset-on-change语法```
reset_on_change=<bool>
```复制描述```
当group by字段的值改变时,是否将累计的统计值重置。只有遇到包含所有group by 字段的事件才会触发这一操作，只有一部分group by 字段的事件会被忽略。当此参数与window一起使用时，window也会被重置。默认为false
```复制current语法```
current=<bool>
```复制描述```
统计是否包含当前event，默认为true
```复制window语法```
window=<int>
```复制描述```
事件数窗口大小，默认为0(即所有事件)
```复制global语法```
global=<bool>
```复制描述```
只有在指定window时生效，决定是否使用单一window还是使用由by字段决定的多个window，默认为true
```复制allnum语法```
allnum=<bool>
```复制描述```
聚合字段截止目前是否全部为数值。当allnum为false时，遇到聚合字段为非数值型会跳过此条日志进行统计，即当前这条日志的统计结果为空；allnum为true时，遇到聚合字段为非数值型时会将此条及以后所有日志的统计值均置为空。默认为false
```复制timefield语法```
timefield=<field>
```复制描述```
指定日志中的时间字段名称，默认为timestamp
```复制
- field-list语法```
<field>(,<field>)*
```复制描述```
分组字段，所有的stats-func-as将在分组内统计
```复制
Example 88. 示例1
window为3以及global为true的情况下，按照生成字段b进行分组并连续统计cnt的distinct count值
```
 | makeresults count=10
 | streamstats window=10 count() as cnt by timestamp
 | eval b = cnt%2
 | streamstats window=3 global=true dc(cnt) as dc_ by b
```
复制
```
说明：
    global为true说明使用一个单一window
    第一行结果就计算的是第1行的事件对应的dc值即为：b为1的时候的dc(cnt)值为1(cnt取值：1)
    第二行结果就计算的是第1-2行的事件对应的dc值为：b为0的时候的dc(cnt)值为1(cnt取值：2)
    第三行结果就计算的是第1-3行的事件对应的dc值为：b为1的时候的dc(cnt)值为2(cnt取值：1，3)
    第四行结果就计算的是第2-4行的事件对应的dc值为：b为0的时候的dc(cnt)值为2(cnt取值为2，4)
    之后以此类推
```
复制
Example 89. 示例2
window为3以及global为false的情况下，按照生成字段b进行分组并连续统计cnt的distinct count值
```
 | makeresults count=10
 | streamstats window=10 count() as cnt by timestamp
 | eval b = cnt%2
 | streamstats window=3 global=false dc(cnt) as dc_ by b
```
复制
```
说明：
    global为false说明使用b的结果作为window的个数(在本题中b有两种值，即0代表一种window，1代表一种window)
    第一行结果就计算的是第1行的事件对应的dc值即为：b为1的时候的dc(cnt)值为1(cnt取值：1)
    第二行结果就计算的是第1-2行的事件对应的dc值为：b为0的时候的dc(cnt)值为1(cnt取值：2)
    第三行结果就计算的是第1-3行的事件对应的dc值为：b为1的时候的dc(cnt)值为2(cnt取值：1，3)
    第四行结果就计算的是第2-4行的事件对应的dc值为：b为0的时候的dc(cnt)值为2(cnt取值为2，4)
    第五行结果就计算的是第3-5行的事件对应的dc值为：b为1的时候的dc(cnt)值为3(由于以1为window的桶内数据未达到3，所以cnt取值为1，3，5)
    之后以此类推
```
复制
Example 90. 示例3
window为3以及reset_after为cnt>5的情况下，按照生成字段b进行分组并连续统计cnt的distinct count值
```
 | makeresults count=10
 | streamstats window=10 count() as cnt by timestamp
 | eval b = cnt%2
 | streamstats reset_after="cnt>5" window=3 global=false dc(cnt) as dc_ by b
```
复制
```
说明：
    global为false说明使用b的结果作为window的个数(即0代表一种window，1代表另一种)
    第一行结果就计算的是第1行的事件对应的dc值即为：b为1的时候的dc(cnt)值为1(cnt取值：1)
    第二行结果就计算的是第1-2行的事件对应的dc值为：b为0的时候的dc(cnt)值为1(cnt取值：2)
    第三行结果就计算的是第1-3行的事件对应的dc值为：b为1的时候的dc(cnt)值为2(cnt取值：1，3)
    第四行结果就计算的是第2-4行的事件对饮的dc值为：b为0的时候的dc(cnt)值为2(cnt取值为2，4)
    第五行结果就计算的是第1-5行的事件对饮的dc值为：b为1的时候的dc(cnt)值为3(cnt取值为1，3，5)
    第六行结果就计算的是第2-6行的事件对饮的dc值为：b为0的时候的dc(cnt)值为3(cnt取值为2，4，6)
    此时reset生效，之前统计的所有历史值清零
    第七行结果就计算的是第7行的事件对饮的dc值为：b为1的时候的dc(cnt)值为1(cnt取值为7)
    第八行结果就计算的是第8行的事件对饮的dc值为：b为0的时候的dc(cnt)值为1(cnt取值为8)
    之后以此类推
```
复制
### 6.61. table
摘要：
```
将查询结果以表格形式展示，并对字段进行筛选，如果日志不包含筛选字段，则用空行显示，支持通配符
```
复制
语法：
```
table <comma-splitted-fieldlist> | <space-splitted-fieldlist>
```
复制
可选参数：
- comma-splitted-fieldlist语法```
<wildcard-field>(,<wildcard-field>)*
```复制描述```
使用逗号分割字段
```复制
- space-splitted-fieldlist语法```
<wildcard-field>(,<wildcard-field>)*
```复制描述```
使用空格分割字段
```复制
- wildcard-field语法```
<field>|<single-quoted-string>|<wildcardfield>
```复制
Example 91. 示例1
将查询中的结果用表格展示并且只显示apache.status和apache.method 字段
```
 * | table apache.status, apache.method
```
复制
结果中有几行空行，是因为这几条日志中， 没有这两个字段
Example 92. 示例2
将查询中的结果用表格展示并且只显示以json.i开始字段
```
* |table json.i*
```
复制
结果中有几行空行，是因为这几条日志中， 没有这两个字段
### 6.62. timechart
摘要：
```
timechart的行为是将时间分桶后的统计行为，相当于bucket | stats by
```
复制
语法：
```
timechart [<timechart-params>]* <stats-single-value-func> [<stats-single-value-func>]* [by <field> <timechart_by_params>*] [where <expression>]
```
复制
必要参数：
- timechart-func-as语法```
avg | min | max | sun | count | distinct_count | first | last | earliest | latest | rate | exact_dc | sumsq | var | stddev | mad | list | top
```复制描述```
与stats命令结合的函数，请参考[#与stats有关的函数]
```复制
可选参数：
- timechart-by-params语法```
[useother=<bool>] | [otherstr=<double-quoted-string>]
```复制参数useother语法```
useother=<bool>
```复制描述```
表示如果限制了limit的大小，落入limit之后的byfield的值是否使用other代替，默认值为false，即不代替并舍弃这些列
```复制otherstr语法```
otherstr=<double-quoted-string>
```复制描述```
useother为true时使用otherstr指定的字符串来代替落入limit之后的byfield的值，默认值为other
```复制
- timechart-params语法```
[sep=<string>] | [format=<string>] | [cont=<bool>] | [limit=<int>] | [bins=<int>] | [span=<TIMESPAN>] | [minspan=<TIMESPAN>] | [startindex=<int>] | [endindex=<int>] | [rendertype=<string>
```复制参数span-str语法```
span=<string>
```复制描述```
表示分桶间隔，格式为数字+单位，与bucket指令span参数的格式相同，单位可以是 s | m | h | d | w | M | q（更多扩展写法详见小节'与搜索结合使用的修饰符')
```复制sep语法```
sep=<string>
```复制描述```
表示by field和统计字段组合时的分隔符，默认值为":"。
如max(agent_send_timestamp) as ma, by logtype：logtype值为apache时，sep="+" 那么组合出来的字段值为ma+apache
这里默认的顺序为统计字段+分隔符+by field，如果想改变顺序，请使用下面format参数
```复制format语法```
format=<string>
```复制描述```
表示规定字段的组合分隔符和组合顺序，默认值为"$AGG:$VAL"。 在这个字段中用$AGG表示统计字段，$VAL表示by field的值，所以一般的写法是format="$AGG$VAL"，此时为字段分隔符，如果想改变组合顺序，可将$VAL和$AGG的顺序反过来，分隔符仍需置于中间位置
```复制cont语法```
cont=<bool>
```复制描述```
表示是否将不连续的时间桶补充为连续，默认为false。因为将时间按照一定的时间间隔进行分桶时，有些桶内可能没有日志或者时间落入桶，此时桶内的所有统计值都为0。默认情况下会将这些桶所在的行去掉，如果置为true则会将这些行补充到结果中。
```复制limit语法```
limit=<int>
```复制描述```
表示限制使用by field值的个数，默认值为无穷大。即若语句中有 max count avg三种统计函数，by field有10种值，那么在不限制limit的情况下将有3*10+1个字段，即结果中有31列。若limit=5，那么将只取byfield的前5个值与统计字段进行组合，结果就只有3*5+1=16列，结果中也将只有这些列的值。
```复制bins语法```
bins=<int>
```复制描述```
表示最多有多少个桶，默认值100。timechart指令的结果中分桶个数由bins、span、minspan共同决定，bins只规定了桶的最多个数，桶的个数和时间间隔也会随着整个查询的timespan而动态调整。
```复制minspan语法```
minspan=<string>
```复制描述```
表示最小分桶间隔，格式与span相同。
```复制startindex语法```
startindex=<int>
```复制描述```
默认值为0，表示从所有桶中的第几个桶开始取，前面的桶对应的行将被舍弃
```复制endindex语法```
endindex=<int>
```复制描述```
默认值为无穷大，表示取到所有桶中的第几个桶，后面的桶对应的行将被舍弃
```复制rendertype语法```
rendertype=<string>
```复制描述```
用于指定绘图的类型，可选值：line(折线图)，area(面积图)，scatter(散点图)，column(柱状图)
```复制
描述：
1. 与bucket | stats by不同的是，timechart结果的字段名和意义将比较特别，特别适合于画图。其结果的字段为固定的_time字段，即分桶后的timestamp值；其余的所有字段为by field与统计结果的排列组合值。
2. 比较特别的是，timechart使用的by field字段只支持by一个field，不支持by一个fieldlist。原因是timechart可以对byfield的取值情况进行限制（如useother），如果by field允许多个，这个参数将存在歧义。
3. timechart只支持统计函数中的单值统计函数，即：avg，min，max，sum，count，dc比如：timechart max(agent_send_timestamp) as ma count() as cnt by logtype假设logtype总共两个值apache和other，那么timechart的字段总共有5个，分别为_time，apache:ma，other:ma，apache:cnt，other:cnt。那么timechart的结果一行的含义将变成：在属于某个timestamp分桶值范围内的logtype值为apache的最大agent_send_timestamp值，logtype值为other的最大agent_send_timestamp值，logtype值为apache的事件数count值，logtype值为other的事件数count值，相当于将bucket | stats的结果进行了字段值重组和一定意义上的行列转置。
|  | 由于timechart是内部相当于bucket|stats by，所以这里会触发stats命令中的by字段的限制，详情见stats命令的NOTE中的group.size以及stats.oneby.group_size配置项timechart的span参数以及minspan，bins之间的关系有span参数（minspan以及bins不生效）没有span参数(minspan以及bins才生效)当前时间范围除以bins得到的值(设为x,并且x有一定的向上取整范围)如果小于minspan则取minspan如果x大于minspan则取x注：如果在没有span参数的时候分桶的值不满足预期则需咨询spl相关研发同事帮忙查看 |
| --- | --- |
Example 93. 示例1
```
tag:timechart|eval x = len(tostring(apache.request_path))|timechart sep="," format="$VAL**$AGG" limit=5 bins=10 minspan=1m span=10m max(x) as ma count() as cnt by apache.geo.city
```
复制
表示字段分割符为**，组合顺序为byfield值+分隔符+统计字段，限制byfield值为5个进行组合，桶最大个数为10个，最小时间分割桶为1分钟一个，时间分割间隔为10分钟一个时，对raw_message字段长度每个桶取最大值为ma字段，对每个桶出现的事件数进行统计为cnt字段，按照apache.geo.city进行分组后的结果。
Example 94. 示例2
```
 * | timechart sep="," format="$VAL**$AGG" limit=3 rendertype="line" bins=200 minspan=1m span=10m max(delay_time) as ma count() as cnt by apache.status
```
复制
表示字段分割符为**，组合顺序为byfield值+分隔符+统计字段，桶最大个数为200个，最小时间分割桶为1分钟一个，时间分割间隔为10分钟一个时，对delay_time字段长度每个桶取最大值为ma字段，对每个桶出现的事件数进行统计为cnt字段，按照apache.status进行分组后绘制成折线图。
### 6.63. timewrap
摘要：
```
对timechart命令的结果进⾏显⽰或者折叠，可以使⽤timewrap命令实现指定时间周期的数据的⽐较，⽐如按天或者按⽉。
```
复制
语法：
```
timewrap <timespan> param-options*
```
复制
必要参数：
- timespan语法```
<int><timeunit>
```复制描述```
描述span的时间跨度. 时间单位支持[s, m, h, d, w, M, q, y（更多扩展写法详见小节'与搜索结合使用的修饰符')]
```复制
可选参数：
- param-options语法```
<align> | <series> | <timeformat> | <timefield>
```复制描述```
可选参数
```复制参数align语法```
align = (now | end)
```复制描述```
指定在按照时间范围进⾏折叠的时候，是对⻬到搜索的结束时间点还是当前时间
```复制series语法```
series = (relative | exact | short)
```复制描述```
指定新的列如何被命名，如果series=relative ，并假设timewrap-span 指定为1d，则字段名分别为0days_before, 1days_before ，如果series=exact ，则使⽤timeformat 指定的格式来对列进⾏命名
```复制timeformat语法```
timeformat = <string>
```复制描述```
如果指定了series=exact，则字段名将按照timeformat来格式化时间戳进⾏命名，例如，指定timeformat= "yyyy-MM-dd",则字段名会显⽰为2017-01-01, 2017-01-08
```复制timefield语法```
timefield = <field> | <single-quoted-string>
```复制描述```
指定时间字段的字段名，默认为_time
```复制
Example 95. 示例1
统计昨天的事件数，并将将上午的数据和下午的数据进行对比
```
starttime="now-1d/d" endtime="now/d" * | timechart span=1h count() as ct  | timewrap 12h  | eval date=formatdate(_time)
```
复制
### 6.64. top
摘要：
```
获取字段出现次数前N的值的集合，输出字段包括field
```
复制
语法：
```
top <size> <field> <param-options>* [<by-fieldlist-clause>]
```
复制
必要参数：
- size语法```
<int>
```复制描述```
返回字段值的个数
```复制
- field语法```
string
```复制描述```
需要求top的字段名
```复制
可选参数：
- param-options语法```
<countfield> | <percentfield>
```复制描述```
top 可选的参数
```复制参数countfield语法```
countfield = <field>
```复制描述```
默认top会输出count字段(count目前为SPL的关键字)，可通过countfield指定字段名
```复制percentfield语法```
percentfield = <field>
```复制描述```
默认top会输出percent字段，可通过percentfield指定取代percent的字段名
```复制
- by-fieldlist-clause语法```
by <field>(,<field>)*
```复制描述```
分组的字段列表，表示先按照field-list分组，在分组内部计算top N的值
```复制
|  | 由于top支持by多个字段,所以这里会与stats命令中的by字段有同样的字段的限制，详情见stats命令的NOTE中的group.size以及stats.oneby.group_size配置项 |
| --- | --- |
Example 96. 示例1
返回top 3的clientip，同时clientip_count字段表示出现次数，clientip_percent表示所占百分比
```
  * | top 3 apache.clientip countfield=clientip_count percentfield=clientip_percent
  * | top 3 apache.clientip countfield=clientip_count percentfield=clientip_percent
```
复制
从结果图中看到，除了想要统计的apache.clientip字段外，还有clientip_count字段表示计数，以及clientip_percent字段表示百分比
Example 97. 示例2
搜索结果按照request_path进行分组，每个分组内返回top 3的apache.clientip。
```
  * | top 3 apache.clientip by apache.request_path
```
复制
按照apache.request_path分组，分别求出对应的出现次数最多的clientip，同时count，percent为默认字段，表示个数和百分
### 6.65. transaction
摘要：
```
将事件分组成交易
```
复制
语法：
```
transaction <field-list> <txn-definition-opt>* <memcontrol-opt>* <trans-states>?
```
复制
必要参数：
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
一个字段或者字段名的列表，事件将根据此字段的值进行分组成各个交易
```复制
- txn-definition-opt语法```
<maxspan>|<maxevents>|<startswith>|<endswith>|<contains>|<timeshift>|<keepopentxn>|<mvlist>|<mvraw>|<nullstr>|<sortfield>|<keeporphans>|<maxpause>
```复制描述```
交易定义选项
```复制参数maxspan语法```
maxspan = <int>(s|m|h|d)
```复制描述```
交易的事件的时间跨度小于maxspan，可以理解为第一条事件的时间戳和最后一条事件的时间戳的跨度不能大于maxspan
```复制maxevents语法```
maxevents = <int>
```复制描述```
一个交易中的最大事件个数
```复制startswith语法```
startswith = eval(<expression>)|<quoted_string>
```复制描述```
搜索或者eval过滤表达式，如果某个事件满足条件，则标志新交易的开始
```复制endswith语法```
endswith = eval(<expression>)|<quoted_string>
```复制描述```
搜索或者eval过滤表达式，如果某个事件满足条件，则标志新交易的结束
```复制contains语法```
containes = eval(<expression>)|<quoted_string>
```复制描述```
判断raw_message里是否包含eval或字符串中的值，字符串可以为正则表达式
```复制timeshift语法```
timeshift = <int>(s|m|h|d)
```复制描述```
为解决transaction结束的时间边界问题引入的参数，意思是手动将时间结束节点延后的时间长度
```复制示例：```
transaction apache.clientip startswith="Android 4.3" timeshift=10m
```复制```
手动将要执行的命令的搜索时间范围结束点延后10min。
```复制```
这样将会使得本来不完整的transaction 在延后的时间段内找到其结束事件，从而变成完整的transaction。timeshift的具体值的设置依赖于实际应用场景和使用经验。
```复制keepopentxn语法```
keepopentxn = <bool>
```复制描述```
是否将找到end但未找到start的transaction从结果中去掉
```复制默认值：```
false，即不保留
```复制mvlist语法```
mvlist = <bool> | <field>(,<field>)*
```复制描述```
指定为bool值时意义为是否将所有字段抽取为单独的多值字段；指定为字段列表时意义为将指定的字段抽取为单独的多值字段
```复制mvraw语法```
mvraw = <bool>
```复制描述```
表示是否将raw_message字段抽取为一个单独的多值字段
```复制默认值：```
false
```复制nullstr语法```
nullstr = <double-quoted-string>
```复制描述```
抽取为多值字段后结果中为空的元素的替换值，默认值为"nullstr"
```复制默认值：```
"nullstr"
```复制sortfield语法```
sortfield = [+|-]field,...
```复制描述```
将一个transaction内的事件按照sortfield指定的顺序进行排列，当指定多个字段时表示第一个字段相等则按第二个字段排序...以此类推，默认为+timestamp
```复制默认值：```
+timestamp
```复制keeporphans语法```
keeporphans = <bool>
```复制描述```
指定事务命令是否应输出不属于任何事务的结果
```复制默认值：```
false，即不输出
```复制maxpause语法```
maxpause= <int>(s|m|h|d)
```复制描述```
指定事务中事件之间暂停的最长时间（以秒、分钟、小时或天为单位）。如果值为负，则禁用最大暂停约束，并且没有限制
```复制默认值：```
-1，即禁用最大暂停约束，且没有限制
```复制
可选参数：
- memcontrol-opt语法```
<maxopentxn> | <maxopenevents> | <keepevicted>
```复制描述```
内存控制选项
```复制参数maxopentxn语法```
maxopentxn = <int>
```复制描述```
维护在内存中的open transaction的个数，采用LRU的策略进行淘汰
```复制maxopenevents语法```
maxopenevents = <int>
```复制描述```
维护在内存中的open transaction中的events的最大数量，LRU策略淘汰
```复制keepevicted语法```
keepevicted = <bool>
```复制描述```
是否输出逐出的事务。通过检查“closed_txn”字段的值，可以将逐出的交易与非逐出的交易区分开来。对于已逐出的交易，“closed_txn”字段设置为 “0” 或 false，对于未逐出或已关闭的事务，字段设置为 “1” 或 true。如果满足以下条件之一，则“closed_txn”字段设置为“1”：maxevents，maxpause，maxspan，startswith。对于 startswith，由于事务命令以相反的时间顺序查看事件，因此它会在满足开始条件时关闭事务。如果未指定这些条件，则输出所有事务，即使所有事务都将“closed_txn”设置为“0”。当达到内存限制时，也可以逐出事务。
```复制默认值：```
false，即不输出逐出的事务
```复制
- trans-states语法```
( <trans_states_in_field> | < trans_states_match> ) (results by flow)?
```复制描述```
根据transaction中的日志匹配出具体状态，形成transaction的状态流
```复制参数trans_states_in_field语法```
with states <field_value>(,<field_value>)* in <field>
```复制描述```
将使用field中的字段值，作为状态的值，该字段值必须包含在field_value列表里
```复制trans_states_match语法```
<trans_state_match> ("," <trans_state_match>)*
```复制描述```
使用trans_state_match列表中的规则对日志进行匹配生成状态
```复制参数trans_state_match语法```
with "<regex>" ("in" <field>)? as <state>
```复制描述```
如果field中的字段值匹配regex成功，则该条日志状态为state
```复制
描述：
```
如果字段列表为多个字段，并不会解释为这些字段的逻辑AND（field1 AND field2 AND field3）或者逻辑或(field1 OR field2 OR field3)，如果字段列表中的字段存在传递关系，transaction命令将试图通过传递关系来进行计算。
```
复制
```
对于下列事件，可能会被归类到一个transaction中：
```
复制
```
host=a
host=a  username=b
username=b age=20
```
复制
```
如果指定了trans_state的参数，将会对transaction中的日志进行状态的匹配，按照时间顺序进行匹配，得到每条日志的状态，如果指定了results by flow参数，则生成状态之间的转换关系，目前匹配方式分为两种：
```
复制
1. 利用某个字段中的值作为状态，with states a, b, c in module results by flow
2. 对日志原文中使用正则匹配进行状态指定，如：```
with "query parse" in message as qp,
with "fetch doc" in message as fd
results by flow
```复制
|  | maxopenevents参数对应的最大值默认为100000，对应配置项为transaction.max_open_events_limit说明：该配置项用于限制maxopenevents的这个参数值，如果在语句中指定的该参数的值超过该配置项，则会报错。复制maxopenevents参数对应的默认值为50000，对应配置项为transaction.max_open_events说明：该配置项为语句中没有指定maxopenevents参数值时，使用的默认参数值复制 |
| --- | --- |
Example 98. 示例1
通过apache.clientip对日志进行关联，按照时间戳排序，包含Receive的日志为一个新的交易的第一条日志，包含Response的为最后一日志，最多包含10条日志，日志的时间跨度最大为5s
```
logtype:apache |  transaction apache.clientip startswith="Android 4.3" endswith="AndroidPhone" maxopenevents = 10
```
复制
从图中可见，以clientip为分组的transaction的起始日志含有”Android 4.3”，并且以含有Android Phone的日志为结束点
Example 99. 示例2
通过apache.clientip对日志关联，每个交易最多包含10条日志，满足apache.status等于200的日志为transaction的第一条日志
```
logtype:apache |transaction apache.clientip startswith=eval(apache.status==200)  maxopenevents = 10
```
复制
Example 100. 示例3
输入以下json日志，使用transaction获取状态转移的信息
```
{"timestamp":"2017-04-12 16:27:14.000", "sid":1, "module":"a"}
{"timestamp":"2017-04-12 16:27:14.000", "sid":2, "module":"a"}
{"timestamp":"2017-04-12 16:27:14.002", "sid":1, "module":"b"}
{"timestamp":"2017-04-12 16:27:14.003", "sid":1, "module":"c"}
{"timestamp":"2017-04-12 16:27:14.003", "sid":2, "module":"c"}
{"timestamp":"2017-04-12 16:27:14.004", "sid":3, "module":"a"}
{"timestamp":"2017-04-12 16:27:14.005", "sid":3, "module":"b"}
```
复制
得到结果如下：
对transaction的flow结果进行统计，生成桑基图:
Example 101. 示例4
搜索到的所有数据按照appname进行聚合(图一)，按照appname进行聚合并且按照json.a进行排序(图二)
```
tag:richard2 | transaction appname
```
复制
图一：
```
tag:richard2 | transaction appname sortfield=+json.a
```
复制
图二：
### 6.66. transpose
摘要：
```
将查询的表格结果进行行列转换
```
复制
语法：
```
transpose [transpose-count] <transpose-row> <transpose-column> <transpose-valueField>
```
复制
必要参数：
- transpose-row语法```
row=<field-list>
```复制描述```
用于识别新生成的行的关键字，相同的row的字段值的原表格将被合并成同一行
```复制参数field-list语法```
<field>(,<field>)*
```复制描述```
字段列表
```复制
- transpose-column语法```
column=<field-list>
```复制描述```
该字段包含的值将被作为新的字段标签
```复制参数field-list语法```
<field>(,<field>)*
```复制描述```
字段列表
```复制
- transpose-valueField语法```
valueField=<field-list>
```复制描述```
该字段的值将被用于表示新生成表格中对应的值
```复制参数field-list语法```
<field>(,<field>)*
```复制描述```
字段列表
```复制
可选参数：
- transpose-count语法```
<int>
```复制描述```
表示有多少行将被用于做转换
```复制
|  | 由于性能的考虑我们该命令最多转换的行数为100000条，对应的配置项为transpose.row_limit，如果需要转换更多的行，则修改该配置项即可。由于性能的考虑我们行列转换后的结果的最大列数为500，对应的配置项为transpose.column_limit，如果需要转换后的结果的列数更多，则修改该配置项即可。 |
| --- | --- |
Example 102. 示例1
将统计结果进行transpose，row字段为apache.method,column字段为apache.status, value字段为cnt
```
* | stats count() as cnt by apache.method, apache.status | transpose row=apache.method column=apache.status valuefield=cnt
```
复制
结果图中可以看到apache.method字段的值作为新生成行的关键字，相同的关键字将被合并，apache.status字段的值将会被作为新的标签，而cnt字段的值则成为了表格里的数值
### 6.67. unpivot
摘要：
```
行转列操作
```
复制
语法：
```
unpivot [<count>] <param-options>*
```
复制
可选参数：
- count语法```
<int>
```复制描述```
可操作的原始结果行数
```复制
- param-options语法```
<column-name> | <header-field>
```复制参数column-name语法```
column_name = <string>
```复制描述```
新生成的结果的首列名称，可以带双引号也可不带
```复制header-field语法```
header_field = <field>
```复制描述```
新生成的结果中，除首列外，其余列名称对应原始结果中该列的内容
```复制
|  | 默认最大可操作行的限制为500，由配置项unpivot.row_size控制复制 |
| --- | --- |
示例:
原始数据:
Example 103. 示例1
将统计结果直接进行行列转换
```
* | unpivot
```
复制
Example 104. 示例2
将统计结果进行行列转换，并指定新列名对应的原始列名字段
```
* | unpivot header_field = group
```
复制
Example 105. 示例3
将统计结果进行行列转换，指定可操作的原始行数，原始列对应的名称，以及新列对应的原始字段。
```
* | unpivot 2 column_name=aaa header_field=group
```
复制
### 6.68. where
摘要：
```
使用表达式对结果进行过滤
```
复制
语法：
```
where <expression> | <field> <in-func>
```
复制
必要参数：
- expression语法```
<expression_function>
```复制描述```
参考eval命令的表达式，但where要求表达式计算结果应该为布尔类型，如果返回true则不过滤当前行的结果，否则任意其他值该行将被过滤掉。
```复制
可选参数：
- in-func语法```
in(x [,y]...)
```复制描述```
给定一个字段和若干指定值，判断字段中的值是否在指定值中存在
```复制
Example 106. 示例1
筛选出所有apache格式且日志中的城市为深圳市的日志后，按照访问路径request_path分组，对每个组求出访问的不同clientip个数，并限制不同的ip数在40到100范围
```
logtype:apache AND apache.geo.city:"深圳市" |  stats dc(apache.clientip) as dc_count by apache.request_path | where dc_count > 40 && dc_count < 100
```
复制
从结果图中可以看到，每个不同的requet_path都会是不同一行，对应一个count值，这个count值就是不同的ip个数，且根据where限制将在40-100之间
### 6.69. xpath
摘要：
```
提供对xml数据的处理和抽取
```
复制
语法：
```
xpath [input=<field>] output=<field> path=<string> [default_value=<string>]
```
复制
必要参数：
- path语法```
<string>
```复制描述```
xpath描述的路径
```复制
- output语法```
<field>
```复制描述```
指定输出字段
```复制
可选参数：
- input语法```
<field>
```复制描述```
指定抽取的字段，默认为raw_message
```复制
- default_value语法```
<string>
```复制描述```
当抽出的值为空时默认填充的值
```复制
Example 107. 示例1
在搜索appname:lyxpath的结果中，抽取字段json.xp中路径为/purchases/book/title的对应的信息写出到lyly字段中
```
appname:lyxpath | xpath input=json.xp output=lyly path="/purchases/book/title"
```
复制
### 6.70. replace
摘要：
```
使用指定字符串替换字段值，可以指定一个或多个字段，仅替换指定字段的值，如果没有指定字段，则替换所有字段
```
复制
语法：
```
replace value-item [,value-item]* [IN <field-list>]
```
复制
必要参数：
- value-item语法```
<source-String> with <target-String>
```复制描述```
用<target-String>替换<source-String> , 支持通配符*以匹配多个字段值,如果<source-string>和<target-string>都含有通配符，则根据*的位置，调整字符串顺序
```复制
可选参数：
- field-list语法```
<field> ( , <field>)*
```复制描述```
指定要替换值的字段，可以指定一个或多个。如果不指定，则替换全部字段
```复制
Example 108. 示例1
将所有值为"192.168.1.1"的字段值替换为"localhost"
```
 * | replace "192.168.1.1" with "localhost"
```
复制
Example 109. 示例2
调整manufacture字段值的顺序，从以"log"开头，调整为以"log"结尾
```
 * | replace "log*" with "*log" in manufacture
```
复制
Example 110. 示例3
调整fruit,fruit1字段值的顺序，如果字段值以a开头e结尾，且中间有字符，则把该字段值替换为"apple"
```
 * | replace "a*e" with "apple" in fruit,fruit1
```
复制
从图中可以看出，fruit以a头e结尾，因此fruit被替换为apple;fruit1不满足条件，因此不会被替换
### 6.71. makemv
摘要：
```
使用分隔符或者带捕获组的正则表达式，将单值字段转换为多值字段。
```
复制
语法：
```
makemv [delim=<string> | tokenizer=<string>] [allowempty=<bool>] <field>
```
复制
必要参数：
- field语法```
<field>
```复制描述```
指定一个要转换成多值的字段。
```复制
可选参数：
- delim语法```
delim=<string>
```复制描述```
指定一个分隔符。在字符串中每遇到一次delim，就做一次分割。
```复制
- tokenizer语法```
tokenizer=<string>
```复制描述```
指定一个带捕获组的正则表达式。每当匹配到一个子串，就用这次匹配的第一个捕获组来创建多值字段的值。
```复制
- allowempty语法```
allowempty=<bool>
```复制描述```
当使用delim作为分割符时，允许结果中出现空字符串。allowempty对于tokenizer无效。
```复制
Example 111. 示例1
使用分隔符将字符串"a,b,c"用逗号分割，结果为["a","b","c"]
```
*|eval testmv="a,b,c"|makemv delim="," testmv
```
复制
Example 112. 示例2
使用正则表达式 (
),? 将字符串"aaa,..bb,c"分割，结果取第一个捕获组 ([^,]
) 对应的值,最终结果为["aaa","..bb","c"]
```
*|eval testmv="aaa,..bb,c"|makemv tokenizer="([^,]+),?" testmv
```
复制
Example 113. 示例3
使用分隔符将字符串"a,,,b,c"用逗号分割，保留空值,最终结果为["a","","","b","c"]
```
*|eval testmv="a,,,b,c"|makemv delim="," allowempty=true testmv
```
复制
从图中可以看出，加上allowempty=true后，空值也被保留下来
### 6.72. localop
摘要：
```
localop命令强制随后的命令都在spl单机执行
```
复制
语法：
```
localop
```
复制
Example 114. 示例1
如果没有localop，这条语句中的eval命令会在分布式引擎执行；加上localop之后，这条语句中的eval命令以及随后的命令都在spl单机执行
```
 * | localop | eval a=123
```
复制
### 6.73. strcat
摘要：
```
连接来自2个或更多字段的值。将字段值和指定字符串组合到一个新字段中
```
复制
语法：
```
strcat [allrequired=<bool>] <source-field>+ <dest-field>
```
复制
必要参数：
- source-field语法```
<field> | <quoted-str>
```复制描述```
指定要连接的字段名称或者带双引号的字符串
```复制
- dest-field语法```
<field>
```复制描述```
指定目标字段的名字，用来保存连接后的结果。目标字段要出现在源字段的后面
```复制
可选参数：
- allrequired语法```
allrequired = <bool>
```复制描述```
指定每个事件中是否需要所有源字段都存在。如果为allrequired=false，则不存在的源字段将被视为空字符串。如果为allrequired=true，则仅当所有源字段都存在时，才将值写入目标字段。默认为false
```复制
Example 115. 示例1
把字段field1，字符串\"abcd\"，字段field2连接，存到字段strcatresult中
```
 * |eval field1=\"10.192.1.1\",field2=\"192.168.1.1\" |strcat field1 \"abcd\" field2 strcatresult
```
复制
Example 116. 示例2
把一个存在的字段field1和一个不存在的字段field3连接，用allrequired=true要求所有源字段都存在。结果中不会有strcatresult字段
```
 * |eval field1=\"10.192.1.1\",field2=\"192.168.1.1\" |strcat allrequired=true field1 field3 strcatresult
```
复制
Example 117. 示例3
把一个集合类型的字段field1和字符串\"abcd\"连接，用allrequired=true要求所有源字段都存在。由于field1是一个空集合，结果中不会有strcatresult字段。
```
 * |eval field1=split(\"\",\".\")|strcat allrequired=true field1 \"abcd\" strcatresult
```
复制
从图中可以看出，由于field1为空，而allrequired=true要求所有源字段都存在，因此strcat命令执行后，结果中没有strcatresult
### 6.74. loadjob
摘要：
```
加载先前完成的定时任务或告警的执行结果。由ID 和type唯一确定一个任务。如果最近一次时间点的结果不存在，则临时运行原始查询。
```
复制
语法：
```
| loadjob <id> ,<type> [<artifact-offset>]
```
复制
必要参数：
- id语法```
id=<int>
```复制描述```
指定一个定时任务或告警的id。
```复制
- type语法```
type=<quoted-string>
```复制描述```
指定job类型，目前我们只支持"savedschedule"。
```复制
可选参数：
- artifact-offset语法```
artifact_offset=<int>
```复制描述```
选择加载最近执行的第几条结果。例如，如果 artifact_offset=1，则将加载最近执行完成的第二条结果。如果artifact_offset=2，将加载第三个最近的结果。如果artifact_offset=0，则加载最新的执行结果。
```复制
Example 118. 示例1
加载id为1的定时任务的最近一次结果。
```
| loadjob id=1,type="savedschedule"
```
复制
### 6.75. accum
摘要：
```
对每个事件中为数字的指定字段进行逐次累加，得到的累加结果会放入该字段或者新字段中。
```
复制
语法：
```
accum <field> [as <new-field>]
```
复制
必要参数：
- field语法```
<field> | <single-quoted-string>
```复制描述```
累加字段，该字段必须包含数字。
```复制
可选参数：
- new-field语法```
<field> | <single-quoted-string>
```复制描述```
新字段，会将累加的结果放入该字段，如果不指定该字段，会将累加结果放入累加字段。
```复制
Example 119. 示例1
对于每一个事件，会计算从第一个事件开始，到当前事件为止到所有响应长度的和，并将该值保存在sum_resp_len字段中。
```
logtype:apache | accum apache.resp_len as sum_resp_len
```
复制
### 6.76. untable
摘要：
```
table指令的逆操作，使用该指令可以将表格的查看方式转换到事件列表的查看方式。
```
复制
语法：
```
untable
```
复制
Example 120. 示例1
以事件列表的查看方式显示，该条指令等价于："*"。
```
* | table * | untable
```
复制
### 6.77. rest
摘要：
```
调用日志易API，返回对应结果
```
复制
语法：
```
rest <url_path> <apikey_field> [count_field] [timeout_field] [rest_field]
```
复制
必要参数：
- apikey_field语法```
apikey=<string>
```复制描述```
API密钥
```复制
- url_path语法```
<url_path>
```复制描述```
请求日志易的API地址
```复制
可选参数：
- count_field语法```
count=<number>
```复制描述```
返回的最大结果数。若不指定或指定为0，则代表不限制
```复制
- timeout_field语法```
timeout=<number>
```复制描述```
指定API请求的超时时间，单位为秒。若不指定或指定为0，则使用默认超时时间60s。
```复制
- rest_field语法```
<field>=<field_value>
```复制描述```
API请求的参数内容
```复制
- field_value语法```
<field> | <string> | <number>
```复制描述```
请求参数值
```复制
Example 121. 示例1
调用日志易API，获取所有可见的AgentGroup列表，限制返回结果数为2
```
|rest /agentgroup/ apikey="user apikey" count=2
```
复制
Example 122. 示例2
调用日志易API，获取所有可见的应用名称包含a的应用列表
```
|rest /apps/ apikey="user apikey" name__contains="a"
```
复制
### 6.78. typeahead
摘要：
```
返回指定前缀的字段信息。返回的最大结果数取决于为size参数指定的值。typeahead命令可以以指定索引为目标，并受时间限制。
```
复制
语法：
```
<prefix_field> [size_field] [index_field]
```
复制
必要参数：
- prefix_field语法```
prefix=<string>
```复制描述```
字段前缀，也可以选择通过【字段:字段值前缀】来根据字段值前缀提示该字段相应的字段值
```复制
可选参数：
- size_field语法```
size=<number>
```复制描述```
返回的最大结果数
```复制
- index_field语法```
index=<field-list>
```复制描述```
指定索引来替代默认索引
```复制
- field-list语法```
<field>[,<field>]*
```复制描述```
索引字段列表
```复制
Example 123. 示例1
返回以app为前缀的字段信息，指定索引为yotta，限制返回条数为5。
```
|typeahead prefix="app" size=5 index=yotta
```
复制
Example 124. 示例2
返回app字段中以a开头的字段值。
```
|typeahead prefix="app:a"
```
复制
### 6.79. history
摘要：
```
查看当前用户的搜索历史，拥有admin角色权限的用户可以查看所有用户的搜索历史
```
复制
语法：
```
history [showall | onlysearch | onlyapp | events]*
```
复制
可选参数：
- showall语法```
showall=<bool>
```复制描述```
取值true会展示所有用户的搜索历史（只针对admin有效），默认为false
```复制
- onlysearch语法```
onlysearch=<bool>
```复制描述```
取值true只展示来自前台界面搜索的历史，不会展示告警、定时任务等非界面搜索历史，默认为false
```复制
- onlyapp语法```
onlyapp=<bool>
```复制描述```
取值true只展示当前app的搜索历史，默认为true
```复制
- events语法```
events=<bool>
```复制描述```
取值true时以事件列表的形式展示搜索历史，默认为false，即以表格形式展示搜索历史
```复制搜索历史字段说明
| 字段名 | 含义 |
| --- | --- |
| beaver.beaver_cost | 执行搜索时的引擎耗时，单位ms |
| domain | 租户名 |
| logid | 该条历史记录的id |
| spl.category | 任务类型 |
| spl.end_ts | spl执行结束时的时间戳 |
| spl.internal_use | 是否为内部使用 |
| spl.is_logtail | 是否为实时窗口任务 |
| spl.max_search_time_range | 用户拥有的最大搜索时长 |
| spl.provenance | 任务类型 |
| spl.result_bytes | 搜索结果所占空间的字节数 |
| spl.result_count | 搜索结果的条数 |
| spl.search_cost | 执行搜索时的spl耗时，单位ms |
| spl.search_state | 搜索任务状态 |
| spl.sid | 搜索任务的唯一标识sid |
| spl.start_search_date | 搜索任务的创建时间 |
| spl.start_ts | 搜索任务开始执行的时间 |
| spl.task_name | 任务名称 |
| spl.total_hits | 搜索语句命中的事件数 |
| spl.trace_id | 该任务的trice_id |
| spl.user_id | 执行搜索任务的用户id |
| spl.app_name | 执行搜索时所在的应用名称 |
| spl.app_id | 执行搜索时所在的应用id |
| spl.query | 执行的搜索语句 |
Example 125. 示例1:
查看该用户今天的前台搜索历史。
```
| history onlysearch=true
```
复制
Example 126. 示例2:
查看今天所有用户的搜索次数。
```
| history showall=true  | stats count() by spl.user_id
```
复制
### 6.80. addcoltotals
摘要：
```
将新结果附加到搜索结果集的末尾。结果包含每个数字字段的总和，也可以指定要汇总的字段。
```
复制
语法：
```
addcoltotals [<field-list>] [labelfield] [label]
```
复制
可选参数：
- field-list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
要汇总的字段是以逗号或者空格分割的字段列表，支持通配符
```复制
- labelfield语法```
labelfield = <string>
```复制描述```
追加到结果集中的列名
```复制
- label语法```
label = <string>
```复制描述```
与labelfield一起在新增的列中添加标签，当labelfield参数不存在时，该参数无意义
```复制
Example 127. 示例1
计算所有字段的总和，并将总和放入结果集中，并添加列名为change_name的新列，标签名为ALL。
```
* | stats count() by ip | addcoltotals labelfield=change_name label=ALL
```
复制
Example 128. 示例2
指定计算列alert.d*，monitor.check_interval 其余数值列均不计算
```
index=lunaxee * | fields alert.duration_time,monitor.check_interval,alert.domain_id,alert.owner_id | addcoltotals alert.d*,monitor.check_interval
```
复制
### 6.81. addtotals
摘要：
```
为每个搜索结果计算所有数值字段的算术和。可以指定需要求和的字段列表。设置col=true时，在末尾添加计算出的新结果表示字段的列和。
```
复制
语法：
```
addtotals <addtotals-param>*
```
复制
可选参数：
- addtotals-param语法```
<row> | <col> | <labelfield> | <label> | <fieldname> | [<field_list>]
```复制描述```
决定求和行为是行求和/列求和/行列求和，指定求和行/列的名称，对求和的行/列进行匹配。
```复制参数row语法```
row = <bool>
```复制描述```
指定是否为每个事件计算<字段列表>的和。总和被放置在一个新的字段中。row的默认值为true。
```复制col语法```
col = <bool>
```复制描述```
指定是否在事件列表的底部添加列和。col的默认值为false。
```复制labelfield语法```
labelfield = <field>
```复制描述```
用于给求列和的结果指定显示字段，该参数仅在col=true时有效。如果结果集中没有指定的字段，则添加一个新字段。
```复制label语法```
label = <string>
```复制描述```
用于为列和指定行标签。如果labelfield参数是结果集中已经存在的字段，标签将出现在该列下；如果labelfield参数创建了一个新字段，标签将出现在新字段的列下。默认值为Total。
```复制fieldname语法```
fieldname = <field>
```复制描述```
用于指定行求和字段的名称。该参数仅在row=true时有效。默认值为Total。
```复制field_list语法```
<field>(,<field>)* | <single-quoted-string>(,<single-quoted-string>)*
```复制描述```
一个或多个用空格分隔的数字字段。如果该参数不为空时，则只有指定的字段被求和。如果该参数为空，则对所有行的数值字段求和。
```复制
Example 129. 示例1
同时求行、列和。列和显示在appname字段下且列和名称为Col Total，行和名称为Row Total。
```
* | eval a=123 | stats count() by appname,a  | addtotals col=true labelfield=appname label="Col Total"  fieldname="Row Total"
```
复制
Example 130. 示例2
计算字段名中包含p或以b开头的字段和，并在名为TotalAmount的字段中保存总和。
```
* | eval b=123 | eval app=456 | eval ab=11 | stats count() by appname,b,app,ab  | addtotals *p*,b*
```
复制
### 6.82. multireport
摘要：
```
multireport 指令可以对同一数据流做不同的处理，最后汇聚输出。
```
复制
语法：
```
multireport <sub-pipeline>*
```
复制
必要参数：
- sub-pipeline语法```
null
```复制描述```
子搜索管道。以管道符开头的不包含数据源指令的 SPL 语句，如`|where k>1|eval value=1`
```复制
Example131.示例1
对命中对数据，进行两种不同的处理，把k为偶数的事件的v设置为0，把k为奇数的事件的v设置为1
```
*|limit 10|streamstats count() as _c |multireport [[| where _c%2==0|eval v=0]] [[| where _c%2==1|eval v=1]]|table _c,v
```
复制
## 7. SPL中使用注释
SPL支持两种形式的注释，可以用来:
- 描述SPL的用途，某个参数的目的，增强维护性
- 调试SPL，比如注释掉从某个命令之后的所有命令
SPL支持两种注释:
- 行注释 // 从开始到行结尾的部分都是注释
- 块注释 /* */ 两个注释块中间的都是注释
注释可以放在搜索或者其他命令的任意位置，但是放在引号内(成对的单引号和双引号)注释不能生效
## 8. Logtail功能
摘要：
- 通过在界面选择一个实时的窗口, 窗口范围限制为5s-1h
- 运行logtail后，界面会持续的刷新该窗口内的结果，包括时间轴和事件列表
- 时间轴的显示规则：如果窗口在1s-10s，时间轴会以100ms为一个单位，如果窗口在10s-5min, 时间轴会以1s为一个单位，如果窗口在5min-1h，时间轴会以1m为一个单位
- 界面大概会每2s-3s刷新变化一次
语法支持：
- 是否使用优化：未使用优化：支持所有命令使用优化：仅支持stats，top命令
|  | 由于logtail支持优化，所以我们在配置项中的logtail.optimization将会指定是否尝试使用优化，默认为使用优化，打开优化可以减少性能消耗，但是在小间隔时会有精度损失，和logtail.optimization_boundary配合使用在打开优化的情况下，我们需要指定在实时窗口大于多少间隔再使用优化，默认为300000ms，对应配置项logtail.optimization_boundary，如需修改优化时间间隔，则修改该配置项即可由于是指定时间段实时返回数据的，所以为了性能的考虑我们将对query查询的最大结果数限制为1000条，对应配置项为logtail.query.max_result_count，如果需要返回更多的query查询结果则修改该配置项即可由于是指定时间段实时返回数据的，所以为了性能的考虑我们将对stats统计的最大结果数默认为20000条，对应的配置项为logtail.stats.max_result_count，如果需要返回更多的stats查询结果则修改该配置项即可 |
| --- | --- |
## 9. Download功能
摘要：
- 本功能意在对查询的结果进行导出和下载
- 功能的入口有两个，分别在搜索和仪表盘。在搜索中，提交搜索后会出现下载按钮，点击下载并填写下载参数后即可将当前查询的结果导出到文件并存储在配置路径中。进入设置-下载管理，可以看到正在执行的下载任务和已经结束的历史下载任务，再次点击右侧下载按钮可将文件通过浏览器下载至本地。
必要参数：
- <文件名>描述：```
填写文件名以标识此次任务并作为导出文件的名称，如在同一用户下出现重名，那么本次下载任务将不被会执行
```复制
- <文件类型>描述：```
对于下载文件格式的限制，总体上提供txt、csv和json三种格式支持，具体限制见下面详细描述
```复制
可选参数：
- <最大下载>描述：```
可限制下载文件的大小或者下载结果的条数。同时系统配置了最大大小和最多条数，如果用户输入的参数超过配置，将会报错
```复制
- <文件编码>描述：```
对于下载文件编码格式的限制，默认为UTF-8，可选为GBK。GBK编码主要是为了解决在windows系统下用excel打开csv格式时内容乱码问题
```复制
语法和格式支持：
```
目前对于Stats类的查询支持csv和json格式，对于Query类的查询支持txt和json格式，对于Transaction类查询仅支持json格式。另外在仪表盘中对于语法的限制遵循仪表盘的说明。
```
复制
|  | 下载功能的每个用户可同时保存的文件数目最大限制为20，对应配置项download.files_per_user_limit，如果需要支持单用户下载保存更多的文件数，则修改该配置即可下载功能的最大条数限制，默认为10000000，对应配置项为download.max_eventscsv文件下载时暂不支持append语句 |
| --- | --- |
## 10. 搜索宏功能
摘要：
- SPL宏是一些SPL命令组织在一起，作为一个单独SPL命令完成一个特定的任务，它能使日常工作变得更容易，并且支持多个参数传入
- 定义SPL宏功能入口为：`设置→资源→搜索宏`，然后可以看到当前配置的所有宏，再次点击右上角的新建按钮即可创建一个SPL宏
必要参数：
- 名称：描述：```
该名称为调用搜索宏的名称及参数个数
```复制
|  | 如果搜索宏使用参数，则需在名称后附加参数的数目来进行表示 |
| --- | --- |
- 示例：```
testMacro(2)
```复制标签：
- 描述：```
该搜索宏的标签
```复制定义：
- 描述：```
即此次新增的宏代表的spl语句，这里的spl语句可以是完整的带query部分的语句，也可以是不带query的只由管道符分割的一组命令。当宏带参数时，需要在定义spl语句中将参数用双 "$" 符号包裹。
```复制
- 示例：```
新增一个名称为mymacro(1)的宏，其定义为 * | stats count() by $X$，X为调用宏时需要传入的字段名，在调用宏的时候使用的语句为：`mymacro(appname)`。
```复制
可选参数：
- 是否使用基于eval的宏的定义：描述：```
要以 eval 命令表达式创建宏定义，请选择使用基于 eval 的表达式?。此设置指定了搜索宏定义是一个返回字符串的 eval 表达式
```复制示例：示例1：```
搜索宏名：mm(2)，宏定义为：if(isstr(a),$x$-$y$,$x$+$y$)，勾选‘使用基于eval的定义’，搜索页搜索 * | eval x=`mm(1,2)`,搜索错误
```复制示例2：```
搜索宏名：mm(2)，宏定义为："if(isstr(a),$x$-$y$,$x$+$y$)"，勾选‘使用基于eval的定义’，搜索页搜索 * | eval x=`mm(1,2)`,搜索正确，x="3"
```复制示例3：```
搜索宏名：mm(2)，宏定义为：if(isstr(a),$x$-$y$,$x$+$y$)，不勾选‘使用基于eval的定义’，搜索页搜索 * | eval x=`mm(1,2)`,搜索正确，x=3
```复制示例4：```
搜索宏名：mm(2)，宏定义为："if(isstr(a),$x$-$y$,$x$+$y$)"，不勾选‘使用基于eval的定义’，搜索页搜索 * | eval x=`mm(1,2)`,搜索正常，x="if(isstr(a),1-2,1+2)"
```复制NOTE：```
上述四种示例中的示例2，即定义中带双引号且勾选eval定义情况下，isstr(a)这里的函数无法传字段名，因为这种情况下宏定义是在语法解析之前也就是拿到数据之前提前执行的，所以无法获取传入字段名和字段值。如若想实现传入字段值进行判断且最终宏替换结果为计算结果的话，请使用第三种示例进行定义。
```复制
- 参数：描述：```
即在上述的必要参数中填写的定义中定义的参数名称，其间使用","分隔
```复制示例：```
x,y
```复制NOTE：```
参数之间以逗号分割，参数名称只能包含字母数字，“_”和“-”字符
```复制
- 验证表达式：描述：```
输入通过宏参数运行的eval或布尔表达式
```复制示例：```
isstr(x) && isstr(y)
```复制
- 验证错误信息：描述：```
输入在验证表达式返回“false”时要显示的信息
```复制示例：```
参数错误，请输入正确的参数
```复制
Example 131. 示例1
新增一个名称为mymacro(1)的宏，其定义为 * | stats count() by $X$，X为调用宏时需要传入的字段名，在调用宏的时候使用的语句为：mymacro(appname)。
```
`mymacro("appname")`
```
复制
新建宏的页面：
使用宏的界面：
## 11. 高基功能(Flink)
摘要：
- 高基模式搜索(SPL on Flink) 旨在解决在做数据统计时，因分组数量(配置项：group.size)的限制而导致的统计结果不全的问题。 如`stats count() by srcip`在srcip 的数量超过 group.size 的限制时，只会返回部分结果。
- 不建议在高基模式使用非统计类型的命令
|  | 目前不支持的命令: iplocation, chart, correlation, dbx系列命令, filldown, geostats, makecontinuous, map, rare, save, timechart, timewrap, transpose, unpivot, gentimes, ldap系列命令, loadjob, multisearch, rest, accum, addcoltotals, addtotals, appendcols, autoregress, eventstats, lookup2, multireport, rollingstd, streamstats, partition, 自定义命令, ML系列命令支持普通搜索、普通告警、定时任务和报表功能。 |
| --- | --- |
## 12. 自定义命令功能
### 12.1. 摘要：
- 自定义命令旨在解决需要用户对数据自定义一些计算时使用，如用户想要将数据做一些复杂的功能时则可以使用该自定义命令来完成
|  | 如需使用自定义命令，必须先保证manager上安装了python模块检查方式：查看/opt/rizhiyi/parcels下有没有python目录)如果没有，安装方式：去 3.4.0.0/3.3.0.0_update_3.4.0.0下载python包并导入manger激活即可。目前仅支持python文件作为执行自定义命令的可执行文件设置chunked参数时需要注意：如果使用v2协议，则需要在python脚本中重写initialized方法并且返回命令类型 |
| --- | --- |
#### 12.1.1. 自定义命令执行文件示例：
1. 生成数据命令示例：脚本含义：用于生成如下10条数据脚本文件：-搜索示例：-
2. 可分布式处理命令示例：脚本含义：用于在当前行加入一个字段名为appname22的值为xxxxx的列脚本文件：-搜索示例：-
3. 集中处理命令示例：脚本含义：用于统计数据中ct字段的累积和脚本文件：-搜索示例：-
4. 格式转换命令示例：脚本含义：将输入数据进行排序(倒序)脚本文件：-搜索示例：-
5. 使用配置文件的arguments参数示例：脚本含义：通过配置文件里面的arguments参数来控制脚本调用不同的计算function脚本文件：-搜索示例：计算count：-计算sum：-
6. 使用spl命令参数示例：脚本含义：通过spl命令中的参数来控制脚本调用不同的计算function脚本文件：-搜索示例：计算count：-计算avg：-
Version 4.1
Last updated 2024-07-01 15:12:32 +0800

---

> 注意: 这是自动下载的文档，可能不是最新版本。请访问 [在线文档](http://log.gf.com.cn/docs/search_reference/) 获取最新信息。

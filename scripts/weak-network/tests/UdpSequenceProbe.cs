// Private UDP test source. Exactly one datagram per sequence; no retries.
using System;using System.IO;using System.Net;using System.Net.Sockets;using System.Diagnostics;using System.Threading;using System.Linq;using System.Text;using System.Web.Script.Serialization;
class UdpSequenceProbe {
 static int Main(string[] a){Console.OutputEncoding=new UTF8Encoding(false);try{
  if(a.Length!=8)throw new Exception("ip port nonce run count pps output drain-ms required");
  var ip=IPAddress.Parse(a[0]);int port=int.Parse(a[1]),run=int.Parse(a[3]),count=int.Parse(a[4]),pps=int.Parse(a[5]),drain=int.Parse(a[7]);
  if(ip.AddressFamily!=AddressFamily.InterNetwork||count<1||count>20000||pps<1||pps>1000||drain<500||drain>10000||a[2].Length!=32)throw new Exception("Invalid bounded test parameters");
  byte[] nonce=Enumerable.Range(0,16).Select(i=>Convert.ToByte(a[2].Substring(i*2,2),16)).ToArray();
  long[] sent=new long[count],received=new long[count];int duplicates=0,foreign=0,receiveErrors=0,sendErrors=0;bool stop=false;
  using(var udp=new UdpClient(new IPEndPoint(IPAddress.Any,0))){udp.Client.ReceiveBufferSize=4*1024*1024;udp.Client.SendBufferSize=1024*1024;udp.Client.ReceiveTimeout=100;udp.Connect(ip,port);
   Console.WriteLine(new JavaScriptSerializer().Serialize(new{ready=true,pid=Process.GetCurrentProcess().Id,local=udp.Client.LocalEndPoint.ToString(),run=run}));Console.Out.Flush();
   if(Console.ReadLine()!="GO")return 2;
   var rx=new Thread(()=>{while(!Volatile.Read(ref stop)){try{IPEndPoint remote=null;byte[] data=udp.Receive(ref remote);long at=Stopwatch.GetTimestamp();
     if(data.Length!=128||data[0]!=87||data[1]!=78||data[2]!=50||data[3]!=80||!nonce.SequenceEqual(data.Skip(4).Take(16))||BitConverter.ToInt32(data,20)!=run){foreign++;continue;}
     int seq=BitConverter.ToInt32(data,24);if(seq<0||seq>=count){foreign++;continue;}if(received[seq]!=0)duplicates++;else received[seq]=at;
    }catch(SocketException ex){if(ex.SocketErrorCode!=SocketError.TimedOut)receiveErrors++;}catch(ObjectDisposedException){break;}}});rx.IsBackground=true;rx.Start();
   long start=Stopwatch.GetTimestamp();byte[] packet=new byte[128];packet[0]=87;packet[1]=78;packet[2]=50;packet[3]=80;Buffer.BlockCopy(nonce,0,packet,4,16);Buffer.BlockCopy(BitConverter.GetBytes(run),0,packet,20,4);
   for(int i=0;i<count;i++){long due=start+(long)(i*(double)Stopwatch.Frequency/pps);while(Stopwatch.GetTimestamp()<due){if((due-Stopwatch.GetTimestamp())*1000.0/Stopwatch.Frequency>2)Thread.Sleep(1);else Thread.SpinWait(30);}
    Buffer.BlockCopy(BitConverter.GetBytes(i),0,packet,24,4);try{if(udp.Send(packet,packet.Length)==packet.Length)sent[i]=Stopwatch.GetTimestamp();else sendErrors++;}catch(SocketException){sendErrors++;}}
   long sendEnd=Stopwatch.GetTimestamp();Thread.Sleep(drain);Volatile.Write(ref stop,true);rx.Join(1500);long finish=Stopwatch.GetTimestamp();
   var result=new{run=run,pid=Process.GetCurrentProcess().Id,count=count,pps=pps,payload_bytes=128,accepted_sends=sent.Count(x=>x!=0),unique_replies=received.Count(x=>x!=0),send_errors=sendErrors,receive_errors=receiveErrors,duplicates=duplicates,foreign_packets=foreign,qpc_frequency=Stopwatch.Frequency,start_qpc=start,send_end_qpc=sendEnd,finish_qpc=finish,sent_qpc=sent,received_qpc=received,receive_buffer=udp.Client.ReceiveBufferSize,send_buffer=udp.Client.SendBufferSize};
   File.WriteAllText(a[6],new JavaScriptSerializer{MaxJsonLength=16*1024*1024}.Serialize(result),new UTF8Encoding(false));Console.WriteLine("DONE");return 0;
  }
 }catch(Exception ex){Console.Error.WriteLine(ex.GetType().Name+": "+ex.Message);return 1;}}
}

// Windows-native inventory, per-process ETW counters, IP Helper and EStats.
// Build: Framework64 csc /platform:x64 /r:System.Web.Extensions.dll /r:System.Drawing.dll.
using System;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Net;
using System.Net.NetworkInformation;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32.SafeHandles;

class NativeCollector {
    static string Root=Directory.GetParent(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)).FullName;
    static string Sid=WindowsIdentity.GetCurrent().User.Value;
    static string PipeName="WeakNetV2-"+String.Join("",System.Security.Cryptography.SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(Root+Sid)).Take(12).Select(b=>b.ToString("x2")));
    static JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=16*1024*1024};
    static object Gate=new object();static volatile bool Stop=false;static HashSet<int> Selected=new HashSet<int>();
    static Dictionary<string,Counter> Counters=new Dictionary<string,Counter>();
    static object Latest=null;static int EtwCode=-1;static uint Lost=0;static long Events=0,Unmapped=0;static string Error=null;
    static ulong Session=0,Trace=UInt64.MaxValue;static IntPtr Props=IntPtr.Zero,LogInfo=IntPtr.Zero,Logger=IntPtr.Zero;
    static string SessionName="WeakNetworkPanelV2.Network",InstanceId=Guid.NewGuid().ToString("N");static double StartedAt=Epoch();
    static EventCallback EventDelegate=OnEvent;static BufferCallback BufferDelegate=OnBuffer;
    static bool SessionStarted=false;static int Cleaned=0;
    static Dictionary<string,Tuple<bool,byte[]>> Enabled=new Dictionary<string,Tuple<bool,byte[]>>();
    static Guid TcpGuid=new Guid("9a280ac0-c8e0-11d1-84e2-00c04fb998a2"),UdpGuid=new Guid("bf3a50c5-a9c9-4988-a005-2df0b7c80f80");
    class Counter {public int pid;public long birth;public string path;public long sent,received,retransmit_events;}
    [DllImport("kernel32.dll")]static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
    [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll")]static extern bool GetProcessTimes(IntPtr h,out long creation,out long exit,out long kernel,out long user);
    [DllImport("kernel32.dll")]static extern void GetSystemTimePreciseAsFileTime(out long value);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern bool GetNamedPipeClientComputerNameW(IntPtr pipe,StringBuilder name,uint length);
    [StructLayout(LayoutKind.Sequential)]struct SecurityAttributes {public int length;public IntPtr descriptor;public int inherit;}
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr CreateNamedPipeW(string name,uint mode,uint pipeMode,uint maxInstances,uint outSize,uint inSize,uint timeout,ref SecurityAttributes attrs);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern bool QueryFullProcessImageName(IntPtr h,uint flags,StringBuilder text,ref int count);
    [DllImport("iphlpapi.dll")]static extern uint GetExtendedTcpTable(IntPtr table,ref int size,bool sort,int family,int tableClass,uint reserved);
    [DllImport("iphlpapi.dll")]static extern uint GetExtendedUdpTable(IntPtr table,ref int size,bool sort,int family,int tableClass,uint reserved);
    [DllImport("iphlpapi.dll")]static extern uint GetPerTcpConnectionEStats(IntPtr row,int type,IntPtr rw,uint rwVer,uint rwSize,IntPtr ros,uint rosVer,uint rosSize,IntPtr rod,uint rodVer,uint rodSize);
    [DllImport("iphlpapi.dll")]static extern uint GetPerTcp6ConnectionEStats(IntPtr row,int type,IntPtr rw,uint rwVer,uint rwSize,IntPtr ros,uint rosVer,uint rosSize,IntPtr rod,uint rodVer,uint rodSize);
    [DllImport("iphlpapi.dll")]static extern uint SetPerTcpConnectionEStats(IntPtr row,int type,IntPtr rw,uint version,uint size,uint offset);
    [DllImport("iphlpapi.dll")]static extern uint SetPerTcp6ConnectionEStats(IntPtr row,int type,IntPtr rw,uint version,uint size,uint offset);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode)]static extern uint StartTraceW(out ulong handle,string name,IntPtr properties);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode)]static extern uint ControlTraceW(ulong handle,string name,IntPtr properties,uint code);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode)]static extern ulong OpenTraceW(IntPtr logfile);
    [DllImport("advapi32.dll")]static extern uint ProcessTrace(ulong[] handles,uint count,IntPtr start,IntPtr end);
    [DllImport("advapi32.dll")]static extern uint CloseTrace(ulong trace);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate void EventCallback(IntPtr trace);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate uint BufferCallback(IntPtr logfile);
    static double Epoch(){return (DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds;}
    static Dictionary<string,object> Obj(params object[] values){var d=new Dictionary<string,object>();for(int i=0;i<values.Length;i+=2)d[(string)values[i]]=values[i+1];return d;}
    static void Atomic(string name,object data){string file=Path.Combine(Root,"data",name),tmp=file+"."+Process.GetCurrentProcess().Id+".tmp";File.WriteAllText(tmp,Json.Serialize(data),new UTF8Encoding(false));for(int i=0;i<20;i++){try{if(File.Exists(file))File.Replace(tmp,file,null);else File.Move(tmp,file);return;}catch(IOException){Thread.Sleep(20);}}throw new IOException("State file busy");}
    static string ProcessPath(int pid,out long born){born=0;IntPtr h=OpenProcess(0x1000,false,pid);if(h==IntPtr.Zero)return null;try{long e,k,u;if(!GetProcessTimes(h,out born,out e,out k,out u))return null;var b=new StringBuilder(32768);int n=b.Capacity;return QueryFullProcessImageName(h,0,b,ref n)?b.ToString():null;}finally{CloseHandle(h);}}
    static string Identity(int pid,long birth){return pid.ToString()+":"+birth.ToString();}
    static void OnEvent(IntPtr e){
        try{Guid guid=(Guid)Marshal.PtrToStructure(IntPtr.Add(e,24),typeof(Guid));if(guid!=TcpGuid&&guid!=UdpGuid)return;byte op=Marshal.ReadByte(e,4);ushort version=(ushort)Marshal.ReadInt16(e,6);if(version<1){Interlocked.Increment(ref Unmapped);return;}int size=Marshal.ReadInt32(e,80);IntPtr data=Marshal.ReadIntPtr(e,72);if(size<8||data==IntPtr.Zero)return;
            int pid=Marshal.ReadInt32(data);uint bytes=(uint)Marshal.ReadInt32(data,4);if(bytes>64*1024*1024)return;long born;string path=ProcessPath(pid,out born);long wall;GetSystemTimePreciseAsFileTime(out wall);long qpc=Stopwatch.GetTimestamp();double eventWall=wall+(Marshal.ReadInt64(e,16)-qpc)*10000000.0/Stopwatch.Frequency;
            if(path==null||born>eventWall){Interlocked.Increment(ref Unmapped);return;}if(op!=10&&op!=26&&op!=11&&op!=27&&op!=14&&op!=30)return;
            lock(Gate){string id=Identity(pid,born);Counter c;if(!Counters.TryGetValue(id,out c)){c=new Counter{pid=pid,birth=born,path=path};Counters[id]=c;}
                if(op==10||op==26)c.sent+=bytes;else if(op==11||op==27)c.received+=bytes;else if(guid==TcpGuid&&(op==14||op==30))c.retransmit_events++;Events++;}
        }catch{Interlocked.Increment(ref Unmapped);}
    }
    static uint OnBuffer(IntPtr p){Lost=(uint)Marshal.ReadInt32(p,416);return Stop?0u:1u;}
    static void StartEtw(){
        // x64 layouts verified against the installed Windows SDK headers.
        Props=Marshal.AllocHGlobal(120+2048);for(int i=0;i<2168;i++)Marshal.WriteByte(Props,i,0);
        Marshal.WriteInt32(Props,0,2168);Marshal.WriteInt32(Props,40,1);Marshal.WriteInt32(Props,44,0x20000);
        byte[] guid=System.Security.Cryptography.SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(Root+Sid)).Take(16).ToArray();Marshal.Copy(guid,0,IntPtr.Add(Props,24),16);
        Marshal.WriteInt32(Props,48,64);Marshal.WriteInt32(Props,52,8);Marshal.WriteInt32(Props,56,64);Marshal.WriteInt32(Props,64,0x02000100);Marshal.WriteInt32(Props,68,1);Marshal.WriteInt32(Props,72,0x10000);Marshal.WriteInt32(Props,116,120);
        byte[] name=Encoding.Unicode.GetBytes(SessionName+"\0");Marshal.Copy(name,0,IntPtr.Add(Props,120),name.Length);
        EtwCode=(int)StartTraceW(out Session,SessionName,Props);if(EtwCode!=0)return;SessionStarted=true;
        Logger=Marshal.StringToHGlobalUni(SessionName);LogInfo=Marshal.AllocHGlobal(448);for(int i=0;i<448;i++)Marshal.WriteByte(LogInfo,i,0);
        Marshal.WriteIntPtr(LogInfo,8,Logger);Marshal.WriteInt32(LogInfo,28,0x1100);Marshal.WriteIntPtr(LogInfo,400,Marshal.GetFunctionPointerForDelegate(BufferDelegate));Marshal.WriteIntPtr(LogInfo,424,Marshal.GetFunctionPointerForDelegate(EventDelegate));
        Trace=OpenTraceW(LogInfo);if(Trace==UInt64.MaxValue){EtwCode=Marshal.GetLastWin32Error();if(EtwCode==0)EtwCode=-2;return;}
        new Thread(()=>{uint result=ProcessTrace(new ulong[]{Trace},1,IntPtr.Zero,IntPtr.Zero);if(!Stop&&result!=0){EtwCode=(int)result;Error="ETW stream ended";}}){IsBackground=true}.Start();
    }
    static int Port(IntPtr p,int offset){ushort x=(ushort)Marshal.ReadInt32(p,offset);return (ushort)IPAddress.NetworkToHostOrder((short)x);}
    static string Ip(IntPtr p,int offset,int bytes,uint scope=0){byte[] a=new byte[bytes];Marshal.Copy(IntPtr.Add(p,offset),a,0,bytes);return bytes==16?new IPAddress(a,scope).ToString():new IPAddress(a).ToString();}
    static Dictionary<string,object> Stats(IntPtr row,bool v6,string id){
        IntPtr rw=Marshal.AllocHGlobal(1),rod=Marshal.AllocHGlobal(160);try{
            Marshal.WriteByte(rw,0);uint code=v6?GetPerTcp6ConnectionEStats(row,3,rw,0,1,IntPtr.Zero,0,0,rod,0,160):GetPerTcpConnectionEStats(row,3,rw,0,1,IntPtr.Zero,0,0,rod,0,160);
            if(code==0&&Marshal.ReadByte(rw)==0){Marshal.WriteByte(rw,1);uint set=v6?SetPerTcp6ConnectionEStats(row,3,rw,0,1,0):SetPerTcpConnectionEStats(row,3,rw,0,1,0);
                if(set!=0)return Obj("status",set==5?"permission_required":"unavailable","error_code",set,"source","Windows EStats");
                if(!Enabled.ContainsKey(id)){byte[] copy=new byte[v6?52:20];Marshal.Copy(row,copy,0,copy.Length);Enabled[id]=Tuple.Create(v6,copy);}
                code=v6?GetPerTcp6ConnectionEStats(row,3,rw,0,1,IntPtr.Zero,0,0,rod,0,160):GetPerTcpConnectionEStats(row,3,rw,0,1,IntPtr.Zero,0,0,rod,0,160);
            }
            if(code!=0||Marshal.ReadByte(rw)==0)return Obj("status","unavailable","error_code",code,"source","Windows EStats");
            uint count=(uint)Marshal.ReadInt32(rod,32*4);
            return Obj("status",count>0?"valid":"waiting","rtt_ms",count>0?(object)(uint)Marshal.ReadInt32(rod,27*4):null,"rtt_variation_ms",count>0?(object)(uint)Marshal.ReadInt32(rod,28*4):null,"retransmitted_segments",(uint)Marshal.ReadInt32(rod,5*4),"retransmitted_bytes",(uint)Marshal.ReadInt32(rod,6*4),"rtt_samples",count,"source","Windows EStats","sampled_at",Epoch());
        }finally{Marshal.FreeHGlobal(rw);Marshal.FreeHGlobal(rod);}
    }
    static List<object> Connections(){var list=new List<object>();HashSet<int> selection;lock(Gate)selection=new HashSet<int>(Selected);
        foreach(int family in new int[]{2,23})foreach(bool tcp in new bool[]{true,false}){
            int length=0;uint first=tcp?GetExtendedTcpTable(IntPtr.Zero,ref length,false,family,5,0):GetExtendedUdpTable(IntPtr.Zero,ref length,false,family,1,0);if(length<=0)continue;
            IntPtr buf=Marshal.AllocHGlobal(length);try{uint result=tcp?GetExtendedTcpTable(buf,ref length,false,family,5,0):GetExtendedUdpTable(buf,ref length,false,family,1,0);if(result!=0)continue;
                int count=Marshal.ReadInt32(buf),stride=tcp?(family==2?24:56):(family==2?12:28);
                for(int i=0;i<count;i++){IntPtr row=IntPtr.Add(buf,4+i*stride);bool v6=family==23;int pid=Marshal.ReadInt32(row,stride-4);string local=v6?Ip(row,0,16,(uint)Marshal.ReadInt32(row,16)):Ip(row,tcp?4:0,4);
                    int localPort=Port(row,v6?20:tcp?8:4);string remote=tcp?(v6?Ip(row,24,16,(uint)Marshal.ReadInt32(row,40)):Ip(row,12,4)):null;int remotePort=tcp?Port(row,v6?44:16):0;int state=tcp?Marshal.ReadInt32(row,v6?48:0):0;
                    string id=pid+"|"+local+":"+localPort+"|"+remote+":"+remotePort;
                    long birth;ProcessPath(pid,out birth);id+="|"+birth;var item=Obj("pid",pid,"birth",birth,"protocol",tcp?"TCP":"UDP","family",v6?"IPv6":"IPv4","local_ip",local,"local_port",localPort,"remote_ip",remote,"remote_port",remotePort,"tcp_state",state,"id",id,"source","Windows IP Helper","sampled_at",Epoch());
                    if(tcp&&selection.Contains(pid)&&state==5)item["estats"]=Stats(row,v6,id);else item["estats"]=Obj("status",tcp&&state==5?"not_selected":"not_applicable","source","Windows EStats");list.Add(item);
                }
            }finally{Marshal.FreeHGlobal(buf);}
        }return list;
    }
    static object Snapshot(){var processes=new List<object>();foreach(Process p in Process.GetProcesses()){try{long born;string path=ProcessPath(p.Id,out born);processes.Add(Obj("pid",p.Id,"birth",born,"name",p.ProcessName+".exe","path",path,"path_status",path==null?"permission_required":"valid"));}catch{}finally{p.Dispose();}}
        List<object> counters;lock(Gate)counters=Counters.Values.Select(c=>(object)Obj("pid",c.pid,"birth",c.birth,"path",c.path,"sent",c.sent,"received",c.received,"retransmit_events",c.retransmit_events)).ToList();
        return Obj("sampled_at",Epoch(),"started_at",StartedAt,"collector_pid",Process.GetCurrentProcess().Id,"collector_id",InstanceId,"admin",new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator),"etw",Obj("status",EtwCode==0?(Events==0?"waiting":Lost>0||Unmapped>0?"partial":"valid"):EtwCode==5?"permission_required":"unavailable","code",EtwCode,"events",Events,"events_lost",Lost,"unmapped_events",Unmapped,"source","Windows ETW TCP/IP + UDP/IP","error",Error),"processes",processes,"connections",Connections(),"counters",counters);
    }
    static void SampleLoop(){while(!Stop){try{object value=Snapshot();lock(Gate)Latest=value;}catch(Exception e){Error=e.Message;}Thread.Sleep(1000);}}
    static string IconFor(string path){if(!File.Exists(path)||!path.EndsWith(".exe",StringComparison.OrdinalIgnoreCase))return null;using(Icon icon=Icon.ExtractAssociatedIcon(path)){if(icon==null)return null;using(Bitmap image=new Bitmap(icon.ToBitmap(),new Size(24,24)))using(MemoryStream m=new MemoryStream()){image.Save(m,ImageFormat.Png);return Convert.ToBase64String(m.ToArray());}}}
    static void SecureSession(){string p=Path.Combine(Root,"data","session.json");var acl=new FileSecurity();acl.SetAccessRuleProtection(true,false);acl.SetOwner(WindowsIdentity.GetCurrent().User);acl.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(Sid),FileSystemRights.FullControl,AccessControlType.Allow));acl.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(WellKnownSidType.LocalSystemSid,null),FileSystemRights.FullControl,AccessControlType.Allow));File.SetAccessControl(p,acl);}
    static NamedPipeServerStream LocalPipe(PipeSecurity security){byte[] bytes=security.GetSecurityDescriptorBinaryForm();IntPtr sd=Marshal.AllocHGlobal(bytes.Length);try{Marshal.Copy(bytes,0,sd,bytes.Length);var attrs=new SecurityAttributes{length=Marshal.SizeOf(typeof(SecurityAttributes)),descriptor=sd,inherit=0};IntPtr h=CreateNamedPipeW("\\\\.\\pipe\\"+PipeName,3|0x80000,8,1,65536,65536,5000,ref attrs);if(h==new IntPtr(-1))throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());return new NamedPipeServerStream(PipeDirection.InOut,false,false,new SafePipeHandle(h,true));}finally{Marshal.FreeHGlobal(sd);}}
    static void RunPipe(){
        StartEtw();new Thread(SampleLoop){IsBackground=true}.Start();
        Atomic("collector-info.json",Obj("pipe",PipeName,"pid",Process.GetCurrentProcess().Id,"admin",new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator),"owner",Sid));
        var security=new PipeSecurity();security.SetAccessRuleProtection(true,false);security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(Sid),PipeAccessRights.FullControl,AccessControlType.Allow));
        while(!Stop){using(var pipe=LocalPipe(security)){
            pipe.WaitForConnection();try{using(var reader=new StreamReader(pipe,new UTF8Encoding(false),false,4096,true))using(var writer=new StreamWriter(pipe,new UTF8Encoding(false),4096,true){AutoFlush=true}){
                string line=reader.ReadLine();if(line==null||line.Length>8192)continue;var request=Json.Deserialize<Dictionary<string,object>>(line);string op=Convert.ToString(request["op"]);object reply;
                if(op=="snapshot"){lock(Gate)reply=Latest??Obj("status","starting");}
                else if(op=="select"){var ids=(System.Collections.IEnumerable)request["pids"];var selected=new HashSet<int>();foreach(object pid in ids){int n=Convert.ToInt32(pid);if(n>0)selected.Add(n);if(selected.Count>512)throw new Exception("Too many processes");}lock(Gate)Selected=selected;reply=Obj("selected",selected.Count);}
                else if(op=="icon"){string path=Convert.ToString(request["path"]);bool known=Process.GetProcesses().Any(p=>{try{long birth;return String.Equals(ProcessPath(p.Id,out birth),path,StringComparison.OrdinalIgnoreCase);}catch{return false;}finally{p.Dispose();}});reply=Obj("png",known?IconFor(path):null);}
                else if(op=="stop"){Stop=true;reply=Obj("stopped",true);}
                else reply=Obj("error","Unsupported operation");writer.WriteLine(Json.Serialize(reply));
            }}catch(Exception ex){Error=ex.Message;}
        }}
    }
    static void Cleanup(){if(Interlocked.Exchange(ref Cleaned,1)!=0)return;Stop=true;if(SessionStarted&&Session!=0&&Props!=IntPtr.Zero)ControlTraceW(Session,SessionName,Props,1);if(Trace!=UInt64.MaxValue)CloseTrace(Trace);Thread.Sleep(1100);
        foreach(var item in Enabled.Values){IntPtr row=Marshal.AllocHGlobal(item.Item2.Length),rw=Marshal.AllocHGlobal(1);try{Marshal.Copy(item.Item2,0,row,item.Item2.Length);Marshal.WriteByte(rw,0);if(item.Item1)SetPerTcp6ConnectionEStats(row,3,rw,0,1,0);else SetPerTcpConnectionEStats(row,3,rw,0,1,0);}finally{Marshal.FreeHGlobal(row);Marshal.FreeHGlobal(rw);}}
    }
    static void PingProbe(string host,int count){var rows=new List<object>();using(var ping=new Ping()){for(int i=0;i<count;i++){var watch=Stopwatch.StartNew();try{var r=ping.Send(host,1500,new byte[32]);rows.Add(Obj("seq",i+1,"sampled_at",Epoch(),"status",r.Status.ToString(),"rtt_ms",r.Status==IPStatus.Success?(object)r.RoundtripTime:null,"address",r.Address==null?null:r.Address.ToString()));}catch(Exception ex){rows.Add(Obj("seq",i+1,"sampled_at",Epoch(),"status","error","error",ex.GetType().Name,"rtt_ms",null));}int wait=1000-(int)watch.ElapsedMilliseconds;if(wait>0)Thread.Sleep(wait);}}
        Console.WriteLine(Json.Serialize(Obj("source","独立ICMP探针","samples",rows)));
    }
    static int Main(string[] args){Console.OutputEncoding=new UTF8Encoding(false);try{
        if(args.Length>0&&args[0]=="--secure-session"){SecureSession();return 0;}
        if(args.Length>0&&args[0]=="--once"){EtwCode=5;Console.WriteLine(Json.Serialize(Snapshot()));return 0;}
        if(args.Length==3&&args[0]=="--ping"){int count=Int32.Parse(args[2]);if(count<1||count>20)throw new Exception("Invalid count");PingProbe(args[1],count);return 0;}
        Directory.CreateDirectory(Path.Combine(Root,"data"));Console.CancelKeyPress+=(s,e)=>{e.Cancel=true;Cleanup();};RunPipe();return 0;
    }catch(Exception e){Console.Error.WriteLine(e.GetType().Name+": "+e.Message);return 1;}finally{Cleanup();}}
}

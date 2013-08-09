<?php
//DNSDB Set up
$dnsdbkey = 'ISCDNSDBKEY--GOES---HERE'
$opts = array('http'=>array('method'=>"GET",'header'=>array("Accept: application/json","X-API-Key: ".$dnsdbkey)));
$streamcontext = stream_context_create($opts);

function get_domain($url)
{
	$pieces = parse_url($url);
	$domain = isset($pieces['host']) ? $pieces['host'] : '';
	if (preg_match('/(?P<domain>[a-z0-9][a-z0-9\-]{1,63}\.[a-z\.]{2,6})$/i', $domain, $regs)) {
		return $regs['domain'];
		}
	return false;
}

try {
  // open connection to MongoDB fill in details in obvious places. collection name should be "whois" or change s/whois/your-name/gi here
  $conn = new Mongo('localhost');
  $db = $conn->test;
  $whoiscoll = $db->whois;
  $wcursor = $whoiscoll->find();
  $querystring = $_SERVER['QUERY_STRING'] ;
  $qcollection = $_GET['coll'] ;
  $key = $_GET['key'];
  $query = rawurldecode($_GET['query']);
  $resnum = 0;
  if (isset($_GET['num'])){
    $resnum = $_GET['num'];
    }
  if (!isset($qcollection) && !isset($_GET['id']) && !isset($_GET['ip'])){
  
    echo '<html><head profile="http://www.w3.org/2005/10/profile"><style type="text/css"><!--A:link {text-decoration: none}A:visited {text-decoration: none}A:active {text-decoration: none}A:hover {text-decoration: underline}--></style>';
    echo '<title>WhoDat? Find and Pivot! </title><body bgcolor="#ffffff" body link="#1A579C" vlink="#1A579C"  alink="#FF0000"><font size="3" face="verdana" color="black"><font color="#494D52"><p align="center"><b><br>';
    echo 'Searching <font color="red">'. $wcursor->count() . '</font> Domains<br>';
    echo '<font size=1><i>Updated Daily At 04:30 EST</i></font><br><br>';
    echo '<table cellpadding="5" border="0" width="90%">';
    echo '<tr><th  bgcolor="#f6f6ef" colspan="4"><font size="3" face="verdana" color="#494D52">Search the WhoDat? Database<font></th></tr>';    
    echo '<tr width="90%">';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><font color="black" size="3"><form method="get" action="' . $PHP_SELF .'"> <i>Select A Key</i><br />';
    echo '<input type="hidden" value="whois" name="coll"/>';
    echo ' <select id="dropDown" name="key">';
    echo '<option value="domainName">Domain Name</option><option value="contactEmail">Contact Email</option><option value="registrant_name">Contact Name</option>';  
    echo '</select> ';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><font color="black" size="3"><i> Search Term <br><input type="text" size="20" maxlength="100" name="query"><br>';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><font color="black" size="3"><i> Concise Results (API) <br><input type="checkbox" name="api" value="yes"  /><br><font size="1"><input type="radio" name="type" value="list">List<input type="radio" name="type" value="csv">CSV<input type="radio" name="type" value="json">Json ';
    echo '<td  bgcolor="#f6f6ef" align="center"><font color="black" size="3"><input type="submit" value="SEARCH" name="submit"></form> ';
    echo '<tr><th  bgcolor="#f6f6ef" colspan="4"><font size="1" face="verdana" color="#494D52">Made by: <a href="mailto:chris@xenosec.org">Chris Clark</a>  &copy <a href="https://xenosec.org/"> XenoSec </a> 2013<font></th></tr>';    
  
    }

  if (isset($qcollection)){
    $querycoll = $db->$qcollection;
    $queryregex = new MongoRegex('/'.$query.'/i');
    $finalquery = array($key => $query);
    $queryresult = $querycoll->find( $finalquery)->timeout(30000)->skip($resnum);
  
    if (isset($_GET['api'])){
      if(isset($_GET['limit'])){
        $apilimit = $_GET['limit'];
        }
      else{
        $apilimit = 2000;
        }
      
      if($_GET['type'] == 'json'){ 
        foreach ($queryresult ->sort(array('domainName' => 1))->limit($apilimit) as $obj){
          echo json_encode($obj);
        }}
      
      elseif($_GET['type'] == 'csv'){
        if (!isset($_GET['nodl'])){
          $fileName = 'whodat_results_'.$_GET['query']. '.csv';
          header("Cache-Control: must-revalidate, post-check=0, pre-check=0");
          header('Content-Description: File Transfer');
          header("Content-type: text/csv");
          header("Content-Disposition: attachment; filename={$fileName}");
          header("Expires: 0");
          header("Pragma: public");}
          
        $fh = @fopen( 'php://output', 'w' );
        $header = False;
        foreach ($queryresult ->sort(array('domainName' => 1))->limit($apilimit) as $obj){
          if($header == False){
            fputcsv($fh, array_keys($obj));
            $header= True;
            }
          fputcsv($fh, $obj);
          }}
      else{ 
        foreach ($queryresult ->sort(array('domainName' => 1))->limit($apilimit) as $obj){
          echo $obj['domainName'] . '<br>';
        }}
    }


  else { 
    echo '<html><head profile="http://www.w3.org/2005/10/profile"><style type="text/css"><!--A:link {text-decoration: none}A:visited {text-decoration: none}A:active {text-decoration: none}A:hover {text-decoration: underline}--></style>';
    echo '<title>WhoDat? Search for '.$query.'</title><body bgcolor="#ffffff" body link="#1A579C" vlink="#1A579C"  alink="#FF0000"><font size="3" face="verdana" color="black"><font color="#494D52"><p align="center"><b><br>';
    echo '<table cellpadding="5" border="0" width="90%">';
    echo '<tr><th  bgcolor="#f6f6ef" colspan=4"><font size="3" face="verdana" color="#494D52">Results <font color="red">'. ($resnum +1).'</font>  to <font color="red">'. ($resnum + 20).'</font>  of <font color="red">' . $queryresult ->count() .' </font><font color="#494D52"> Matches for <font color="red">' . strtoupper($query) . '</font> in the <font color="red">' . ucfirst($key) . ' </font>Key</th></tr>';
    echo '<tr width="90%">';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><a name="newsearch"><font color="black" size="3"><form method="get" action="' . $PHP_SELF .'"> <i>Select A Key</i><br />';
    echo '<input type="hidden" value="whois" name="coll"/>';
    echo ' <select id="dropDown" name="key">';
    echo '<option value="domainName">Domain Name</option><option value="contactEmail">Contact Email</option><option value="registrant_name">Contact Name</option>';
    echo '</select> ';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><font color="black" size="3"><i> Search Term <br><input type="text" size="20" maxlength="100" name="query"><br>';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top"><font color="black" size="3"><i> Concise Results (API) <br><input type="checkbox" name="api" value="yes"  /><br><font size="1"><input type="radio" name="type" value="list">List<input type="radio" name="type" value="csv">CSV<input type="radio" name="type" value="json">Json ';
    echo '<td  bgcolor="#f6f6ef" align="center" width="140"><font color="black" size="3"><input type="submit" value="SEARCH" name="submit"></form> ';
    echo '<tr width="90%"><td bgcolor="#f6f6ef" align="center"  colspan="4"><font color="#494D52" size="2"><b>';
    if ($resnum >= 20){
      echo ' <a href="index.php?'. $querystring .'&num='. ($resnum - 20) .'" >Last 20</a>';
      }
    else {
      echo '<a href="'. $_SERVER['HTTP_REFERER']. '"  >Go Back</a>';
      }
    echo ' <---<a href="#newsearch" > New Search </a> ---> <a href="index.php?'. $querystring .'&num='. ($resnum + 20) .'" > Next 20</a></b>';

    foreach ($queryresult ->sort(array('standardRegCreatedDate' => -1))->limit(20) as $obj){
    if (strtolower($qcollection) == 'whois'){
      echo '<tr width="90%"><td  bgcolor="#f6f6ef" rowspan="3" colspan="3"><font color="black" size="2">';	
      echo  '<font color="red" > <b>Domain:</font><a href="index.php?id='. $obj['domainName'].'"> '.  $obj['domainName'] . '</a></b> <br/>';
      echo  '<font color="#494D52" size="2"><b>Name: </b><a href="index.php?coll=whois&key=registrant_name&query='. $obj['registrant_name'].'">' . $obj['registrant_name'] . '<br/></a></b>';
      echo  '<font color="#494D52" size="2"><b>Email: </b></font><a href="index.php?coll=whois&key=contactEmail&query='. $obj['contactEmail'].'">' . $obj['contactEmail'] . '<br/></a></b>';
      echo  '<font color="#494D52" size="2"><b>Address:</b><font color="black"> '. $obj['registrant_street1'].' '.$obj['registrant_street2'].' '.$obj['registrant_street3'].' '.$obj['registrant_street4'].' '.$obj['registrant_city'].' '.$obj['registrant_state'].' '.$obj['registrant_postalCode'].' '.$obj['registrant_country']. '<br/></b>';
      $currentres = gethostbyname($obj['domainName']);
      echo  '<font color="#494D52" size="2"><b>Current IP: <b><a href="index.php?ip=' . $currentres.'">'.$currentres.'</a>'; 
      echo '<td bgcolor="#f6f6ef" width="60"><font color="black" size="1">';
      echo  '<font color="#494D52"> <b>Created:</font> '. substr($obj['standardRegCreatedDate'], 0, 10) . ' <br/>';
      echo '<tr><td  bgcolor="#f6f6ef" width="60" height="10"  padding:"0"><font color="black" size="1" >';
      echo  '<font color="#494D52"> <b>Updated:</font> '.  substr($obj['standardRegUpdatedDate'], 0, 10) . ' <br/>';
      echo '</td></tr>';
      echo '<tr><td  bgcolor="#f6f6ef" width="60" height="10" padding:"0" ><font color="black" size="1">';
      echo  '<font color="red"> <b>Expires:</font> '.  substr($obj['standardRegExpiresDate'], 0, 10) . ' <br/>';
      echo '</td></tr>';
      echo '<tr width="90%"><td  bgcolor="#f6f6ef" colspan="4" ><font color="black" size="1"> ';
      echo '<b><i>Matches in Key </i><font color=#494D52> '. $key .'</font> </i>: </b>';	
      
      if (is_array($obj[$key])){
        foreach ($obj[$key] as $value){
          $highlighted = preg_replace('/'.$query.'/i', '<font color="red"><b>'.$query.'</b></font>', htmlspecialchars($value));
          echo $highlighted . ' '; 
      		}
        }
      else{
        $highlighted = preg_replace('/'.$query.'/i', '<font color="red"><b>'.$query.'</b></font>', htmlspecialchars($obj[$key]));
        echo $highlighted; 
        }
		
      }
      }
      echo '<tr width="90%"><td bgcolor="#f6f6ef" align="center"  colspan="4"><font color="#494D52" size="2"><b>';
      if ($resnum >= 20){
        echo ' <a href="index.php?'. $querystring .'&num='. ($resnum - 20) .'" >Last 20</a>';
        }
      else {
        echo '<a href="'. $_SERVER['HTTP_REFERER']. '"  >Go Back</a>';
        }
      echo ' <---<a href="#newsearch" > New Search </a> ---> <a href="index.php?'. $querystring .'&num='. ($resnum + 20) .'" > Next 20</a></b>';
      echo '<tr><th  bgcolor="#f6f6ef" colspan="4"><font size="1" face="verdana" color="#494D52">Made by: <a href="mailto:chris@xenosec.org">Chris Clark</a>  &copy <a href="https://xenosec.org/"> XenoSec </a> 2013<font></th></tr>';    
      echo  '</td></tr></table></body></html>' ;
      }	
      }
    
  if (isset($_GET['id'])){ 
    if(substr($_GET['id'], 0, 4) == "www."){
      $_GET['id'] = substr($_GET['id'],4);
      }  
    $domaindata = $whoiscoll->findOne(array('domainName' => $_GET['id'])); 
    echo '<html><head profile="http://www.w3.org/2005/10/profile"><style type="text/css"><!--A:link {text-decoration: none}A:visited {text-decoration: none}A:active {text-decoration: none}A:hover {text-decoration: underline}--></style>';
    echo '<title>WhoDat? '.$_GET['id'].'</title><body bgcolor="#ffffff" body link="#1A579C" vlink="#1A579C"  alink="#FF0000"><font size="3" face="verdana" color="black"><font color="#494D52"><p align="center"><b><br>';
    echo '<table cellpadding="5" border="0" width="90%">';
    echo '<tr><th  bgcolor="#f6f6ef" colspan="4"><font size="3" face="verdana" ><b>Details For<font color="#494D52"> '.$_GET['id'].'</font></b></th></tr>';
    echo '<tr width="90%">';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top">';
    echo '<b><font color="black" size="2"><a href="'. $_SERVER['HTTP_REFERER']. '"  > Go Back To Search Results </a><br></td></tr>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3"><b>ISC Passive DNS Results</b><font size="2"> (Limit 100)</font> </td></tr>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3">';
    $dnsdb = file_get_contents('https://api.dnsdb.info/lookup/rrset/name/*.'.$domaindata["domainName"].'/a/?limit=100', false, $streamcontext);
    if($dnsdb != Null){
      echo '<table><tr><td>Domain</td><td>IP Address</td><td>First Seen</td><td>Last Seen</td></tr>';
      foreach(preg_split("/((\r?\n)|(\r\n?))/", $dnsdb) as $line){
        $dnsarray = json_decode($line, TRUE);
        if($dnsarray !=Null){
          echo '<tr><td>'. substr($dnsarray['rrname'], 0 , -1) .'</td><td><a href="index.php?ip=' . $dnsarray['rdata']['0'] .'">' . $dnsarray['rdata']['0'] .'</a></td><td>' . date('M d Y',$dnsarray['time_first']) .'</td><td>' .  date('M d Y',$dnsarray['time_last']);
          }}
    echo '</table>';
    }
    else{
      echo "No ISC DNSDB Results";
    }
    echo '</tr></td>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3"><b>Complete WhoIs Data for<font color="#494D52"> '.$_GET['id'].'</font><b></td></tr>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3">';
    $currentres = gethostbyname($_GET['id']);
    echo  'Current IP : <a href="index.php?ip=' . $currentres.'">'.$currentres.'</a><br>'; 
    foreach ($domaindata as $dkey => $dval){
      if ($dkey == "contactEmail" or $dkey == "registrant_name" or $dkey == "domainName"){
        echo $dkey. ' : <a href="index.php?coll=whois&key='.$dkey.'&query='.$dval.'">' .$dval .'</a><br>' ;
        }
      elseif ($dkey != "_id" && $dval != Null){
			 echo $dkey. ' : <font color="#494D52">' .$dval .'</font><br>' ;
        }
      } 
    echo '<tr><th  bgcolor="#f6f6ef"><font size="1" face="verdana" color="#494D52">Made by: <a href="mailto:chris@xenosec.org">Chris Clark</a>  &copy <a href="https://xenosec.org/"> XenoSec </a> 2013<font></th></tr>';    
    }

  if (isset($_GET['ip'])){
    $ip = $_GET['ip'];
    echo '<html><head profile="http://www.w3.org/2005/10/profile"><style type="text/css"><!--A:link {text-decoration: none}A:visited {text-decoration: none}A:active {text-decoration: none}A:hover {text-decoration: underline}--></style>';
    echo '<title>WhoDat? '.$ip.'</title><body bgcolor="#ffffff" body link="#1A579C" vlink="#1A579C"  alink="#FF0000"><font size="3" face="verdana" color="black"><font color="#494D52"><p align="center"><b><br>';
    echo '<table cellpadding="5" border="0" width="90%">';
    echo '<tr><th  bgcolor="#f6f6ef" colspan="4"><font size="3" face="verdana" ><b>Details For<font color="#494D52"> '.$ip.'</font></b></th></tr>';
    echo '<tr width="90%">';
    echo '<td  bgcolor="#f6f6ef" align="center" valign="top">';
    echo '<b><font color="black" size="2"><a href="'. $_SERVER['HTTP_REFERER']. '"  > Go Back To Search Results </a><br></td></tr>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3"><b>ISC Passive DNS Results </b><font size="2"> (Limit 200)</font> </td></tr>';
    echo '<tr><td align="left" bgcolor="#f6f6ef"><font size="3">'; 
    $ipdb = file_get_contents('https://api.dnsdb.info/lookup/rdata/ip/'.$ip.'/a/?limit=200', false, $streamcontext);
    if($ipdb != Null){
      echo '<table><tr><td>Domain</td><td>IP Address</td><td>First Seen</td><td>Last Seen</td></tr>';
      foreach(preg_split("/((\r?\n)|(\r\n?))/", $ipdb) as $line){  
        $iparray = json_decode($line, TRUE);
        if($iparray !=Null){
          echo '<tr><td><a href="index.php?id='.substr($iparray['rrname'], 0,-1).'">'.substr($iparray['rrname'], 0, -1).'</a></td><td>' . $iparray['rdata'] .'</td><td>' .  date('M d Y',$iparray['time_first']) .'</td><td>' . date('M d Y',$iparray['time_last'])  ;
          }}
    echo '</table>';
    }
    else{
      echo "No ISC DNSDB Results";
    }
    echo '</tr></td>';
    echo '<tr><th  bgcolor="#f6f6ef"><font size="1" face="verdana" color="#494D52">Made by: <a href="mailto:chris@xenosec.org">Chris Clark</a>  &copy <a href="https://xenosec.org/"> XenoSec </a> 2013<font></th></tr>';    
  }

  $conn->close();
} catch (MongoConnectionException $e) {
  die('Error connecting to MongoDB server');
} catch (MongoException $e) {
  die('Error: ' . $e->getMessage());
}
?>
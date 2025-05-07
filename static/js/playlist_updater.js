let loading=true;

function fetchLiveData() {
	fetch("/get_live_info").then(response => response.json()).then(data => {
		document.getElementById("playlistName").innerHTML = "Musi playlist name: "+data.name;
		if (data.scraped!=data.songs){
			document.getElementById("scraped").innerHTML=data.scraped+"/"+data.songs+" songs loaded from playlist"
			document.getElementById("matched").innerHTML="<br>"
		}
		else{
			document.getElementById("scraped").innerHTML="Musi playlist loaded"
			document.getElementById("matched").innerHTML="Searched for "+data.matched+"/"+data.songs+" songs on Spotify"
		}
		
		let notFoundTableBody = document.getElementById('notFoundTableBody');
		notFoundTableBody.innerHTML = ''; 
		if (data.not_found.length>0){
			document.getElementById("notFoundContainer").style.display="block";
		}
		else{
			document.getElementById("notFoundContainer").style.display="none";
		}
		data.not_found.forEach(song => {
			let row = document.createElement('tr');

			let Cell = document.createElement('td');
			let Link = document.createElement("a");
			Link.setAttribute("href", song["url"])
			let LinkText = document.createTextNode(song["title"]+" by "+song["artist"]);
			Link.appendChild(LinkText);
			Cell.appendChild(Link);

			let ButtonCell = document.createElement('td');
			let Button = document.createElement("button");
			Button.addEventListener("click", selectSong, false);
			Button.url=song.url;
			Button.sp_url=""
			let ButtonText = document.createTextNode("Select");
			Button.appendChild(ButtonText);
			ButtonCell.appendChild(Button);
	
			row.appendChild(Cell);
			row.appendChild(ButtonCell);

			notFoundTableBody.appendChild(row);
		});
			
		let foundTableBody = document.getElementById('foundTableBody');
		foundTableBody.innerHTML = '';

		data.matches.forEach(match => {
			let row = document.createElement('tr');

			let ytCell = document.createElement('td');
			let ytLink = document.createElement("a");
			ytLink.setAttribute("href", match["yt_url"])
			let ytLinkText = document.createTextNode(match["yt_title"]+" by "+match["yt_author"]);
			ytLink.appendChild(ytLinkText);
			ytCell.appendChild(ytLink);
		
			let spCell = document.createElement('td');
			let spLink = document.createElement("a");
			spLink.setAttribute("href", "http://open.spotify.com/track/"+match["sp_id"])
			let spLinkText = document.createTextNode(match["sp_title"]+" by "+match["sp_artist"]);
			spLink.appendChild(spLinkText);
			spCell.appendChild(spLink);
			
			let ButtonCell = document.createElement('td');
			let Button = document.createElement("button");
			Button.addEventListener("click", selectSong, false);
			Button.url=match["yt_url"];
			Button.sp_url=spLink.href
			let ButtonText = document.createTextNode("Select");
			Button.appendChild(ButtonText);
			ButtonCell.appendChild(Button);

			row.appendChild(ytCell);
			row.appendChild(spCell);
			row.appendChild(ButtonCell);

			foundTableBody.appendChild(row);
		});
		
		loading=data.loading;
		
		if (data.songs!=0 && data.matched==data.songs){
			document.getElementById("matchUpdater").style.display="block";
			document.getElementById("scraped").innerHTML=""
			document.getElementById("matched").innerHTML="Finished searching for "+data.matched+"/"+data.songs+" songs on Spotify"
			clearInterval(intervalId);
		}
		else if (!data.loading){
			window.location.replace("/error");
		}
	})
}

function selectSong(event){
	if (loading){
		alert("Please wait for all songs to be searched for. This service only searches spotify once, and after that searches are much faster. If you need to run the search on the playlist a second time, it will not take long, so please wait.");
		return false;
	}
	let yt_url=event.currentTarget.url
	let sp_url=event.currentTarget.sp_url
	fetch("/get_song", {method: "POST", body: JSON.stringify({url:yt_url})}).then(response => response.json()).then(data => {
		document.getElementById("selectedSection").style.display='block';
		document.getElementById("isSelected").innerHTML = "Selected video:";
		document.getElementById("selectedVideo").innerHTML = data.yt_title;
		document.getElementById("selectedVideo").href = yt_url;
		document.getElementById("matchedSong").value = sp_url;
		if (sp_url==""){
			document.getElementById("removeButton").style.display="none";
		}
		else{
			document.getElementById("removeButton").style.display="block";
		}
	});
}

function update_match(){
	let url=document.getElementById("matchedSong").value;
	if (url.startsWith("http://open.spotify.com/track/") || url.startsWith("https://open.spotify.com/track/") || url.startsWith("open.spotify.com/track/")){
		if (url.indexOf("?")>-1){
			url=url.substring(0,url.indexOf("?"));
		}
		console.log(url);
	}
	else if (url!=""){
		alert("Format invalid. Make sure you're copying the correct link!");
		document.getElementById("matchedSong").value="";
		return false;
	}
	let yt_url=document.getElementById("selectedVideo").href;
	fetch("/update_match", {method: "POST", body: JSON.stringify({yt_url:yt_url,sp_url:url,remove:false})}).then(response => response.json()).then(data => {
		console.log(data);
		if (data.message=="Success"){
			fetchLiveData();
			alert("Successfully updated match");
			cancel_selection();
		}
		else{
			document.getElementById("matchedSong").value="";
			alert(data.message);
		}
	});
	return false;
}

function remove_match(){
	let url=document.getElementById("matchedSong").value;
	if (url.startsWith("http://open.spotify.com/track/") || url.startsWith("https://open.spotify.com/track/") || url.startsWith("open.spotify.com/track/")){
		if (url.indexOf("?")>-1){
			url=url.substring(0,url.indexOf("?"));
		}
		console.log(url);
	}
	else if (url!=""){
		alert("Format invalid. Make sure you're copying the correct link!");
		document.getElementById("matchedSong").value="";
		return false;
	}
	let yt_url=document.getElementById("selectedVideo").href;
	fetch("/update_match", {method: "POST", body: JSON.stringify({yt_url:yt_url,sp_url:url,remove:true})}).then(response => response.json()).then(data => {
		console.log(data);
		if (data.message=="Success"){
			fetchLiveData();
			alert("Successfully removed match");
			cancel_selection();
		}
		else{
			document.getElementById("matchedSong").value="";
			alert(data.message);
		}
	});
	return false;
}

function cancel_selection(){
	document.getElementById("selectedSection").style.display='none';
	document.getElementById("isSelected").innerHTML = "Select a song below:";
}

var intervalId = window.setInterval(function(){
	fetchLiveData()
}, 1000);
(async function() {
  var accounts = ["AggregateOsint","KnightsOSINT","Global_OSINT22","AsianOSINT","Vantagemonitor","defenseaffairs"];
  var ct0 = document.cookie.match(/ct0=([^;]+)/)?.[1];
  for (var i = 0; i < accounts.length; i++) {
    var name = accounts[i];
    try {
      var r1 = await fetch("/i/api/1.1/users/show.json?screen_name=" + name, {
        headers: {
          "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
          "x-csrf-token": ct0,
          "x-twitter-auth-type": "OAuth2Session"
        }
      });
      var user = await r1.json();
      if (user.following) { console.log("= Already following @" + name); continue; }
      var r2 = await fetch("/i/api/1.1/friendships/create.json", {
        method: "POST",
        headers: {
          "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
          "x-csrf-token": ct0,
          "x-twitter-auth-type": "OAuth2Session",
          "content-type": "application/x-www-form-urlencoded"
        },
        body: "user_id=" + user.id_str
      });
      if (r2.ok) console.log("Followed @" + name);
      else console.log("Failed @" + name + ": " + r2.status);
      await new Promise(function(r) { setTimeout(r, 2000); });
    } catch(e) { console.log("Error @" + name + ": " + e.message); }
  }
  console.log("Done!");
})();

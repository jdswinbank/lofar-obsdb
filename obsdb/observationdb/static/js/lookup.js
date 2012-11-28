// Original by Stuart R. Lowe, http://www.strudel.org.uk/
// Downloaded from http://www.strudel.org.uk/lookUP/ 2012-11-28

// Modified for use at http://msss.astron.nl/ by John Swinbank

var http_request = false;

function getLookUPResults(jData) {
	if(jData == null){
		alert("There was a problem parsing search results");
		return;
	}
	var equinox = jData.equinox;
	var target = jData.target;
	var coordsys = jData.coordsys;
	var ra = jData.ra
	var dec = jData.dec;
	var category = jData.category;
	var service = jData.service;
	var image = jData.image;
    var el = document.getElementById("lookUPresults");
    if (ra && dec && equinox == "J2000" ) {
        id_ra.value = ra.decimal;
        id_dec.value = dec.decimal;
        $('#lookUpSearch').modal('hide')
        el.innerHTML = "<p>Found " + target.name + ".</p>";
        return;
    } else {
        el.innerHTML = "<p>" + target.name + " not found.</p>"
        return;
    }
}

function lookUP(form) {
	var object = form['name'].value
	if(object){
		var el = document.getElementById("lookUPresults")
		if(el){
			el.innerHTML = "Searching..."
		}
		var headID = document.getElementsByTagName("head")[0];
		var newScript = document.createElement('script');
		newScript.type = 'text/javascript';
		newScript.src = 'http://www.strudel.org.uk/lookUP/json/?name='+encodeURIComponent(object)+'&callback=getLookUPResults';
		headID.appendChild(newScript);
	}
}
//function iDidMean(object) {
//	el = document.getElementById('lookUPform');
//	el['name'].value = object
//	lookUP(el)
//}

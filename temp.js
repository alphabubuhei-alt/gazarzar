

    window.showLogin = function() { document.getElementById('authOverlay').style.display = 'flex'; };
    window.hideLogin = function() { document.getElementById('authOverlay').style.display = 'none'; };
    window.showPhoneStep = function() { document.getElementById('phoneStep').style.display = 'block'; document.getElementById('codeStep').style.display = 'none'; };
    window.requestOTP = function() {
        const phone = document.getElementById('loginPhone').value;
        if (phone.length < 8) { showToast('Дугаараа зөв оруулна уу!'); return; }
        document.getElementById('phoneStep').style.display = 'none';
        document.getElementById('codeStep').style.display = 'block';
        showToast('Баталгаажуулах код илгээлээ.');
    };
    window.verifyOTP = function() {
        const phone = document.getElementById('loginPhone').value;
        const code = document.getElementById('loginCode').value;
        if (code.length < 4) { showToast('Кодоо оруулна уу!'); return; }
        isLoggedIn = true;
        localStorage.setItem('gz_token', 'local-auth-' + phone);
        localStorage.setItem('gz_phone', phone);
        showToast('Амжилттай нэвтэрлээ!');
        hideLogin();
        checkAuth();
    };
    window.checkAuth = function() {
        const token = localStorage.getItem('gz_token');
        if (token) {
            isLoggedIn = true;
            const headerAuth = document.getElementById('headerAuth');
            if (headerAuth) headerAuth.innerHTML = `<div class="header-icon-btn" onclick="logout()"><i data-lucide="log-out"></i></div>`;
            lucide.createIcons();
        }
    };
    window.logout = function() {
        localStorage.removeItem('gz_token');
        localStorage.removeItem('gz_phone');
        isLoggedIn = false;
        location.reload();
    };
    window.showSearch = function() { document.getElementById('searchOverlay').style.display = 'flex'; };
    window.hideSearch = function() { document.getElementById('searchOverlay').style.display = 'none'; };
    
    window.applyFilters = function() {
        fetchListings(typeof currentTab !== 'undefined' && currentTab === 'home' ? 'map' : 'grid');
    };

    window.clearFilters = function() {
        if (document.getElementById('headerSearchInput')) document.getElementById('headerSearchInput').value = '';
        if (document.getElementById('minPrice')) document.getElementById('minPrice').value = '';
        if (document.getElementById('maxPrice')) document.getElementById('maxPrice').value = '';
        if (document.getElementById('minPriceMain')) document.getElementById('minPriceMain').value = '';
        if (document.getElementById('maxPriceMain')) document.getElementById('maxPriceMain').value = '';
        if (document.getElementById('filterAreaRange')) document.getElementById('filterAreaRange').value = 'all';
        if (document.getElementById('filterType')) document.getElementById('filterType').value = 'all';
        if (document.getElementById('filterRooms')) document.getElementById('filterRooms').value = 'all';
        if (typeof gridFilters !== 'undefined') gridFilters = { q: '', minPrice: '', maxPrice: '', type: 'all', rooms: 'all', area: 'all' };
        if (typeof mapFilters !== 'undefined') mapFilters = { q: '', minPrice: '', maxPrice: '', type: 'all', rooms: 'all', area: 'all' };
        if (typeof gridCategory !== 'undefined') gridCategory = 'all';
        if (typeof mapCategory !== 'undefined') mapCategory = 'all';
        renderCategories();
        fetchListings('grid');
        fetchListings('map');
    };

    window.showToast = function(msg) {
        const container = document.getElementById('toastContainer');
        const t = document.createElement('div');
        t.className = 'toast';
        t.innerText = msg;
        container.appendChild(t);
        setTimeout(() => t.style.opacity = '1', 10);
        setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 500); }, 3000);
    };





    const firebaseConfig = {
      apiKey: "AIzaSyAQTs6GUwXzrqtvxzFUN3OLIl81uJWfBzI",
      authDomain: "gazara-d0a86.firebaseapp.com",
      projectId: "gazara-d0a86",
      storageBucket: "gazara-d0a86.firebasestorage.app",
      messagingSenderId: "289929939329",
      appId: "1:289929939329:web:d0978c8b3eb52e2210c080"
    };
    firebase.initializeApp(firebaseConfig);
    const db = firebase.firestore();

    const API_BASE = "http://localhost:8080/api";
    let heroMap, postMap, markersGroup, postMarker;
    let isLoggedIn = false;
    let selectedLatLng = null;
    let currentStep = 1;
    const ADMIN_PHONE = "99910230"; // ТАНЫ ДУГААР ЭНД БАЙНА
    window.cachedAgents = [];
    let allFirebaseListings = [];

    // Setup Firebase Realtime Listener
    db.collection("listings").orderBy("createdAt", "desc").limit(200).onSnapshot(snapshot => {
        allFirebaseListings = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            allFirebaseListings.push({ 
                id: doc.id, 
                ...data,
                boost: data.boost || data.boost_status === 'active' || false
            });
        });

        // Sync global master list
        const localListings = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
        const firebaseIds = new Set(allFirebaseListings.map(p => p.id));
        const uniqueLocalListings = localListings.filter(p => !firebaseIds.has(p.id));
        window.allProperties = [...uniqueLocalListings, ...allFirebaseListings];

        if (typeof fetchListings === 'function') {
            fetchListings('grid');
            fetchListings('map');
        }
        if (typeof renderAdminDashboard === 'function') {
            const adminEl = document.getElementById('viewAdmin');
            if (adminEl && adminEl.classList.contains('active')) {
                renderAdminDashboard();
            }
        }
    }, error => {
        console.error("Firebase Snapshot Error:", error);
        if(error.message.includes("Missing or insufficient permissions")) {
            setTimeout(() => {
                if (typeof showToast === 'function') showToast("Firebase алдаа: Датабааз руу хандах эрхгүй байна (Rules шалгана уу)", true);
            }, 2000);
        }
    });

    let mapProperties = [];
    let gridProperties = [];
    let allProperties = []; // Global master list for Admin/Profile
    let mapCategory = 'all';
    let gridCategory = 'all';

    let mapFilters = { q: '', minPrice: '', maxPrice: '', type: 'all', rooms: 'all', area: 'all' };
    let gridFilters = { q: '', minPrice: '', maxPrice: '', type: 'all', rooms: 'all', area: 'all' };

    window.initMap = function() {
        heroMap = L.map('heroMap', { zoomControl: true, attributionControl: false }).setView([47.915, 106.915], 13);
        L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', { maxZoom: 22 }).addTo(heroMap);
        markersGroup = L.layerGroup().addTo(heroMap);
        fetchListings('map');
    }

    window.toggleDrop = function(id) {
        const d = document.getElementById(id);
        const active = d.classList.contains('show');
        document.querySelectorAll('.dropdown-menu').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.filter-pill').forEach(el => el.classList.remove('active'));
        if (!active) {
            d.classList.add('show');
            d.parentElement.querySelector('.filter-pill').classList.add('active');
        }
    }

    async function fetchListings(target = 'grid') {
        const isMap = target === 'map';
        const grid = isMap ? document.getElementById('mapListingsGrid') : document.getElementById('listingsGrid');
        if (grid) grid.innerHTML = Array(isMap ? 4 : 6).fill('<div class="skeleton skeleton-card"></div>').join('');
        
        let q, minPrice, maxPrice, listingType, rooms, areaRange, cat, sort;

        if (isMap) {
            q = mapFilters.q || "";
            minPrice = mapFilters.minPrice || "";
            maxPrice = mapFilters.maxPrice || "";
            listingType = mapFilters.type || "all";
            rooms = mapFilters.rooms || 'all';
            areaRange = mapFilters.area || 'all';
            cat = mapCategory;
            sort = 'new';
        } else {
            q = document.getElementById('headerSearchInput')?.value?.trim() || gridFilters.q || "";
            minPrice = document.getElementById('minPriceMain')?.value || gridFilters.minPrice || "";
            maxPrice = document.getElementById('maxPriceMain')?.value || gridFilters.maxPrice || "";
            listingType = document.getElementById('filterType')?.value || gridFilters.type || "all";
            rooms = document.getElementById('filterRooms')?.value || gridFilters.rooms || 'all';
            areaRange = document.getElementById('filterAreaRange')?.value || gridFilters.area || 'all';
            cat = gridCategory;
            sort = document.getElementById('sortOrderTop')?.value || 'new';
        }
        
        let minArea = "";
        let maxArea = "";
        if (areaRange !== 'all') {
            const parts = areaRange.split('-');
            minArea = parts[0];
            maxArea = parts[1] === 'plus' ? '' : parts[1];
        }

        try {
            // Local fallback logic using the merged data
            const localListings = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
            const firebaseIds = new Set(allFirebaseListings.map(p => p.id));
            const uniqueLocalListings = localListings.filter(p => !firebaseIds.has(p.id));
            
            let fallbackData = [...uniqueLocalListings, ...allFirebaseListings];

            if (q) fallbackData = fallbackData.filter(p => (p.title||'').toLowerCase().includes(q.toLowerCase()) || (p.addr||p.address||'').toLowerCase().includes(q.toLowerCase()));
            if (minPrice) fallbackData = fallbackData.filter(p => (p.priceVal||p.price||0) >= parseFloat(minPrice) * 1000000);
            if (maxPrice) fallbackData = fallbackData.filter(p => (p.priceVal||p.price||0) <= parseFloat(maxPrice) * 1000000);
            if (minArea !== "") fallbackData = fallbackData.filter(p => (p.area||0) >= parseFloat(minArea));
            if (maxArea !== "") fallbackData = fallbackData.filter(p => (p.area||0) <= parseFloat(maxArea));
            if (rooms !== 'all') { const rInt = parseInt(rooms); if (rInt >= 4) fallbackData = fallbackData.filter(p => (p.rooms||1) >= 4); else fallbackData = fallbackData.filter(p => (p.rooms||1) === rInt); }
            if (cat !== 'all') fallbackData = fallbackData.filter(p => p.category === cat);
            if (listingType !== 'all') fallbackData = fallbackData.filter(p => p.listing_type === listingType || p.type === (listingType==='sale'?'Зарна':'Түрээслүүлнэ'));

            let properties = fallbackData.map(p => {
                const priceVal = p.priceVal || p.price || 0;
                return {
                    ...p,
                    priceVal: priceVal,
                    priceLabel: priceVal >= 1000000000 ? (priceVal/1000000000).toFixed(1) + ' тэрбум ₮' : (priceVal/1000000).toFixed(0) + ' сая ₮',
                    lat: p.lat || 47.915,
                    lng: p.lng || 106.915,
                    type: p.type || (p.listing_type === 'sale' ? 'Зарна' : 'Түрээслүүлнэ'),
                    rooms: p.rooms || 1,
                    area: p.area || 0,
                    title: p.title || 'Зар',
                    addr: p.addr || p.address || p.district || 'Улаанбаатар',
                    img: p.img || p.primary_image || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80',
                    desc: p.desc || p.description || 'Дэлгэрэнгүй мэдээлэл байхгүй.',
                    agent: p.agent || p.owner_name || 'Агент',
                    phone: p.phone || '99XX-XXXX',
                    boost: p.boost || p.boost_status === 'active' || false,
                    role: p.role || p.owner_role || 'user',
                    category: p.category || 'apartment'
                };
            });

            if (sort === 'low') properties.sort((a, b) => a.priceVal - b.priceVal);
            else if (sort === 'high') properties.sort((a, b) => b.priceVal - a.priceVal);
            else properties.sort((a, b) => {
                const timeA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
                const timeB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
                return timeB - timeA;
            });

            if (isMap) { 
                mapProperties = properties; 
                renderListings(mapProperties, 'map'); 
            } else { 
                gridProperties = properties; 
                allProperties = properties; 
                renderListings(gridProperties, 'grid'); 
            }

        } catch (error) {
            console.warn(`Error processing listings:`, error);
        }
    }

    function formatMapPrice(price) {
        if (!price) return 'Үнэгүй';
        if (price >= 1000000000) return (price / 1000000000).toFixed(1).replace(/\.0$/, '') + 'b';
        if (price >= 1000000) return (price / 1000000).toFixed(2).replace(/\.00$/, '').replace(/0$/, '') + 'm';
        if (price >= 1000) return (price / 1000).toFixed(0) + 'k';
        return price.toLocaleString();
    }



    window.syncSortAndApply = function(el) {
        document.getElementById('sortOrderTop').value = el.value;
        document.getElementById('sortOrderMain').value = el.value;
        applyFilters();
    }

    function renderListings(data, target = 'grid') {
        const isMap = target === 'map';
        const grid = isMap ? document.getElementById('mapListingsGrid') : document.getElementById('listingsGrid');
        if (!grid) return;
        
        // Sort: Boosted first for display
        data.sort((a, b) => (b.boost ? 1 : 0) - (a.boost ? 1 : 0));

        if (!data || data.length === 0) {
            grid.innerHTML = `
                <div class="no-results" style="grid-column: 1/-1; padding: 40px; text-align: center;">
                    <h3 style="font-size:18px;">🔍 Илэрц олдсонгүй</h3>
                    <p style="color:var(--text-muted); font-size:13px; margin-top:8px;">Шүүлтүүрээ өөрчилж үзнэ үү.</p>
                </div>`;
            if (isMap) markersGroup.clearLayers();
            return;
        }

        if (isMap) {
            markersGroup.clearLayers();
            data.forEach(p => {
                const shortPrice = formatMapPrice(p.priceVal);
                const wrapperClass = p.boost ? 'z-color-gold' : (p.role === 'agent' ? 'z-color-blue' : 'z-color-green');
                const iconHtml = `
                    <div class="z-marker-wrapper ${wrapperClass}">
                        <div class="z-bubble">${shortPrice}</div>
                        <div class="z-dot"></div>
                    </div>
                `;
                const icon = L.divIcon({ className:'z-icon', html: iconHtml, iconSize:[60, 60], iconAnchor: [30, 45] });
                L.marker([p.lat, p.lng], {icon}).addTo(markersGroup).on('click', () => openDetail(p.id));
            });
            
            const countText = `${data.length.toLocaleString()} зар олдлоо`;
            const countMain = document.getElementById('listingsCountMain');
            if (countMain) countMain.innerText = countText;

            grid.innerHTML = data.slice(0, 40).map(p => `
                <div class="property-card" onclick="openDetail('${p.id}')" style="border-radius:16px; overflow:hidden;">
                    <div style="height:110px; background:url('${p.img}') center/cover; position:relative;">
                        <div style="position:absolute; bottom:8px; left:8px; background:rgba(0,0,0,0.6); color:white; font-size:10px; padding:2px 8px; border-radius:4px; backdrop-filter:blur(4px);">${p.area}м²</div>
                    </div>
                    <div style="padding:10px; min-height:80px; display:flex; flex-direction:column; justify-content:center;">
                        <div style="font-weight:800; font-size:14px; color:var(--primary);">${p.priceLabel}</div>
                        <div style="font-size:11px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:2px;">${p.title}</div>
                        <div style="font-size:10px; color:var(--accent-dark); margin-top:4px; font-weight:700;">${p.rooms} өрөө</div>
                    </div>
                </div>
            `).join('');
        } else {
            grid.innerHTML = data.map(p => {
                const cardClass = p.boost ? 'card-gold' : (p.role === 'agent' ? 'card-blue' : 'card-green');
                const tagClass = p.boost ? 'tag-gold' : (p.role === 'agent' ? 'tag-blue' : 'tag-green');
                const tagText = p.boost ? '⭐ BOOST' : (p.role === 'agent' ? 'АГЕНТ' : 'ЭНГИЙН');
                return `
                <div class="property-card ${cardClass}" onclick="openDetail('${p.id}')">
                    <div class="card-img" style="background-image: url('${p.img}')">
                        <div class="card-tag ${tagClass}">${tagText}</div>
                        <div class="card-heart" onclick="event.stopPropagation(); saveListing('${p.id}')">♡</div>
                    </div>
                    <div class="card-body">
                        <div class="card-price-row">
                            <span class="card-price">${p.priceLabel}</span>
                            <span class="card-size">${p.area >= 10000 ? (p.area / 10000) + ' га' : (p.area || 0) + ' м²'}</span>
                        </div>
                        <div class="card-info">${p.rooms || 1} өрөө • ${p.type}</div>
                        <div class="card-addr"><span>📍</span> ${p.addr}</div>
                    </div>
                </div>
                `;
            }).join('');
        }
    }


    window.openDetail = function(id) {
        const p = allProperties.find(x => x.id == id);
        if(!p) return;

        document.getElementById('detailModal').style.display = 'flex';
        
        const images = [p.img, p.img.replace('w=1200', 'w=1201'), p.img.replace('w=1200', 'w=1202')];
        const slider = document.getElementById('modalSlider');
        const dots = document.getElementById('modalDots');
        
        slider.innerHTML = images.map(img => `<div class="gallery-slide" style="background-image:url('${img}')"></div>`).join('');
        dots.innerHTML = images.map((_, i) => `<div class="gallery-dot ${i===0?'active':''}" onclick="document.getElementById('modalSlider').scrollTo({left:${i}*document.getElementById('modalSlider').offsetWidth, behavior:'smooth'})"></div>`).join('');
        
        slider.onscroll = () => {
            const index = Math.round(slider.scrollLeft / slider.offsetWidth);
            document.querySelectorAll('.gallery-dot').forEach((dot, i) => dot.classList.toggle('active', i === index));
        };

        const catMap = { 'apartment': { n: 'Орон сууц', i: 'building' }, 'yard_house': { n: 'Хашаа байшин', i: 'fence' }, 'house': { n: 'Хаус', i: 'home' }, 'land': { n: 'Газар', i: 'map' }, 'office': { n: 'Оффис', i: 'briefcase' } };
        const catInfo = catMap[p.category] || { n: 'Орон сууц', i: 'building' };

        document.getElementById('modalMainInfo').innerHTML = `
            <div class="detail-meta-small" style="font-size:14px; margin-bottom:12px;">
                <span style="background:var(--bg); padding:4px 12px; border-radius:6px;">📍 ${p.addr}</span>
                <span style="background:var(--bg); padding:4px 12px; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                    <i data-lucide="${catInfo.i}" style="width:14px; height:14px;"></i> ${catInfo.n}
                </span>
            </div>
            <h2 style="font-family:'Playfair Display', serif; font-size:32px; margin-top:8px; line-height:1.2;">${p.title}</h2>
            <div class="detail-price-large" style="font-size:36px; margin:16px 0;">${p.priceLabel}</div>
            <div class="detail-meta-small" style="font-weight:700; color:var(--primary); font-size:16px; border-top:1px solid #eee; padding-top:20px; display:flex; justify-content:space-between;">
                <span>${p.rooms} өрөө</span>
                <span>${p.area} м²</span>
                <span>${p.type}</span>
            </div>
        `;
        document.getElementById('modalDesc').innerText = p.desc;
        
        document.getElementById('agentCard').innerHTML = `
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="width:56px; height:56px; border-radius:50%; background:url('https://i.pravatar.cc/100?u=${p.agent}') center/cover; border:2px solid white; box-shadow:var(--shadow-sm);"></div>
                <div style="flex:1;">
                    <div style="font-weight:800; font-size:18px; color:var(--primary);">${p.agent}</div>
                    <div style="font-size:12px; color:var(--text-muted);">${p.role === 'agent' ? 'Мэргэжлийн Агент' : 'Хувь хүн'}</div>
                </div>
            </div>
            <div style="margin-top:20px; padding:12px; background:white; border-radius:12px; border:1px solid #eee; display:flex; align-items:center; gap:10px;">
                <div style="width:32px; height:32px; border-radius:50%; background:var(--accent); color:white; display:flex; align-items:center; justify-content:center; font-size:14px;">📞</div>
                <div class="card-phone-val" style="font-weight:800; font-size:15px; color:var(--primary);">${p.phone || '99XX-XXXX'}</div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    };

    window.closeDetail = function() {
        document.getElementById('detailModal').style.display = 'none';
    };

    // ── POST AD WIZARD LOGIC ──────────────────
    window.showPostAd = function() {
        if (!isLoggedIn) { showToast('Зар оруулахын тулд нэвтэрнэ үү!'); showLogin(); return; }
        document.getElementById('postAdOverlay').style.display = 'flex';
        initPostMap();
        currentStep = 1;
        updateStepUI();
    };
    window.hidePostAd = function() {
        document.getElementById('postAdOverlay').style.display = 'none';
    };
    function initPostMap() {
        if (!postMap) {
            postMap = L.map('postMap', { zoomControl: true, attributionControl: false }).setView([47.915, 106.915], 12);
            L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', { maxZoom: 22 }).addTo(postMap);
            postMap.on('click', (e) => {
                if (postMarker) postMap.removeLayer(postMarker);
                postMarker = L.marker(e.latlng).addTo(postMap);
                selectedLatLng = e.latlng;
                document.getElementById('coordsText').innerText = `Координат: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
            });
        }
        setTimeout(() => postMap.invalidateSize(), 300);
    }
    window.searchPostLoc = async function() {
        const q = document.getElementById('postAddressSearch').value;
        if (!q) return;
        try {
            const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}`);
            const d = await r.json();
            if (d && d.length > 0) {
                const loc = [parseFloat(d[0].lat), parseFloat(d[0].lon)];
                postMap.setView(loc, 15);
                if (postMarker) postMap.removeLayer(postMarker);
                postMarker = L.marker(loc).addTo(postMap);
                selectedLatLng = { lat: loc[0], lng: loc[1] };
            }
        } catch(e) {}
    };
    window.nextStep = function() {
        if (currentStep === 1 && !selectedLatLng) { showToast('Байршил сонгоно уу!'); return; }
        if (currentStep === 2) {
            if (!document.getElementById('postTitle').value) { showToast('Гарчиг оруулна уу!'); return; }
            if (!document.getElementById('postPrice').value) { showToast('Үнэ оруулна уу!'); return; }
            if (!document.getElementById('postPhone').value) { showToast('Утасны дугаар оруулна уу!'); return; }
        }
        if (currentStep < 3) {
            currentStep++;
            updateStepUI();
        } else {
            submitAd();
        }
    };
    window.prevStep = function() {
        if (currentStep > 1) {
            currentStep--;
            updateStepUI();
        }
    };
    function updateStepUI() {
        document.querySelectorAll('.wiz-dot').forEach((s, i) => s.classList.toggle('active', i + 1 === currentStep));
        document.querySelectorAll('.step-content').forEach((s, i) => s.classList.toggle('active', i + 1 === currentStep));
        document.getElementById('prevBtn').style.visibility = currentStep === 1 ? 'hidden' : 'visible';
        document.getElementById('nextBtn').innerText = currentStep === 3 ? 'ЗАР НИЙТЛЭХ' : 'ҮРГЭЛЖЛҮҮЛЭХ';
    }
    window.handleMediaSelect = function(e) {
        const files = e.target.files;
        const preview = document.getElementById('mediaPreview');
        preview.innerHTML = '';
        Array.from(files).slice(0, 10).forEach(f => {
            const reader = new FileReader();
            reader.onload = (ev) => {
                const div = document.createElement('div');
                div.style = `height:100px; border-radius:12px; background:url('${ev.target.result}') center/cover;`;
                preview.appendChild(div);
            };
            reader.readAsDataURL(f);
        });
    };
    async function submitAd() {
        try {
            const title = document.getElementById('postTitle').value;
            const price = document.getElementById('postPrice').value;
            const area = document.getElementById('postArea').value;
            const type = document.getElementById('postType').value;
            const category = document.getElementById('postCategory').value;
            const address = document.getElementById('postAddressSearch').value;
            const description = document.getElementById('postDesc').value;
            const phone = document.getElementById('postPhone').value;
            
            if (!title) { showToast('Гарчиг оруулна уу!'); return; }
            if (!price) { showToast('Үнэ оруулна уу!'); return; }
            if (!phone) { showToast('Утасны дугаар оруулна уу!'); return; }
            if (!selectedLatLng) { showToast('Байршил сонгоно уу!'); return; }

            showToast('Зар хадгалж байна...');

            const userPhone = localStorage.getItem('gz_phone') || phone;
            const priceVal = parseFloat(price) * 1_000_000;
            
            // Handle uploaded photos (base64)
            let imgUrl = 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80';
            const mediaInput = document.getElementById('mediaInput');
            if (mediaInput && mediaInput.files && mediaInput.files[0]) {
                imgUrl = await new Promise(resolve => {
                    const reader = new FileReader();
                    reader.onload = e => {
                        const img = new Image();
                        img.onload = () => {
                            try {
                                const canvas = document.createElement('canvas');
                                let width = img.width, height = img.height;
                                if (width > 800) { height *= 800 / width; width = 800; }
                                canvas.width = width; canvas.height = height;
                                canvas.getContext('2d').drawImage(img, 0, 0, width, height);
                                resolve(canvas.toDataURL('image/jpeg', 0.7));
                            } catch (err) {
                                resolve('https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80');
                            }
                        };
                        img.onerror = () => resolve('https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80');
                        img.src = e.target.result;
                    };
                    reader.onerror = () => resolve('https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80');
                    reader.readAsDataURL(mediaInput.files[0]);
                });
            }

            const newListing = {
                id: 'local_' + Date.now(),
                title: title,
                priceVal: priceVal,
                priceLabel: priceVal >= 1_000_000_000 ? (priceVal/1_000_000_000).toFixed(1) + ' тэрбум ₮' : (priceVal/1_000_000).toFixed(0) + ' сая ₮',
                area: parseFloat(area) || 0,
                listing_type: type,
                type: type === 'sale' ? 'Зарна' : 'Түрээслүүлнэ',
                category: category,
                addr: address || 'Улаанбаатар',
                desc: description,
                lat: selectedLatLng.lat,
                lng: selectedLatLng.lng,
                img: imgUrl,
                agent: userPhone,
                phone: phone,
                rooms: parseInt(document.getElementById('postRooms')?.value) || 1,
                boost: false,
                role: 'user',
                createdAt: new Date().toISOString()
            };

            try {
                await db.collection("listings").add(newListing);
            } catch (e) {
                console.error("Error adding document: ", e);
                showToast("Алдаа: Датабааз руу хуулагдсангүй (Firebase Rules шалгана уу)");
                // Fallback to local storage if Firebase fails
                const saved = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
                saved.unshift(newListing);
                localStorage.setItem('gz_local_listings', JSON.stringify(saved));
            }

            hidePostAd();
            document.getElementById('successOverlay').style.display = 'flex';
            
            // Refresh listings to show the new one
            fetchListings('grid');
            fetchListings('map');
        } catch (err) {
            console.error("submitAd error:", err);
            showToast('Зар нэмэхэд алдаа гарлаа: ' + err.message, true);
        }
    }



    window.toggleSheet = function() {
        const sheet = document.getElementById('mapBottomSheet');
        sheet.classList.toggle('expanded');
    };

    window.saveListing = async function(id) {
        if (!isLoggedIn) { showToast('Зар хадгалахын тулд нэвтэрнэ үү!'); showLogin(); return; }
        try {
            const response = await fetch(`${API_BASE}/listings/${id}/save`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('gz_token')}` }
            });
            if (response.ok) {
                showToast('Зар амжилттай хадгалагдлаа! ♥️');
            } else {
                const data = await response.json();
                showToast(data.detail || 'Хадгалахад алдаа гарлаа.');
            }
        } catch (e) {
            console.error("Хадгалахад алдаа гарлаа:", e);
            showToast('Хадгалахад алдаа гарлаа.');
        }
    }

    const FALLBACK_AGENTS = [];

    function renderAgentCard(a) {
        const badgeHtml = a.badge === 'top' ? '<span style="background:#ffc107;color:#000;font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;">⭐ ТОП</span>' :
            a.badge === 'verified' ? '<span style="background:#28a745;color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;">✔ Баталгаажсан</span>' :
            a.badge === 'new' ? '<span style="background:#007bff;color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;">🆕 Шинэ</span>' : '';
        
        const avatar = a.avatar_url || a.image || 'https://i.pravatar.cc/150?u=agent';
        const districtStr = Array.isArray(a.districts) ? a.districts.join(', ') : (a.districts || '');
        
        return `<div onclick="openAgentProfile(${a.id})" style="background:white;border-radius:16px;padding:24px;box-shadow:var(--shadow-sm);border:1px solid var(--border);display:flex;align-items:center;gap:20px;cursor:pointer;transition:0.2s;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 10px 20px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='var(--shadow-sm)';">
            <div style="width:80px;height:80px;border-radius:50%;background:url('${avatar}') center/cover;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="font-size:18px;font-weight:800;">${a.name||'Агент'}</span>${badgeHtml}
                </div>
                <div style="font-size:13px;color:var(--text-muted);margin-bottom:6px;">${a.company||'Үл хөдлөх хөрөнгийн мэргэжилтэн'}</div>
                <div style="display:flex;gap:16px;font-size:12px;font-weight:600;">
                    <span style="color:#f59e0b;">⭐ ${a.rating||'5.0'}</span>
                    <span style="color:var(--primary-solid);">🏠 ${a.listings_count||0} зар</span>
                    <span style="color:#666;">✅ ${a.total_sales||0} борлуулалт</span>
                </div>
                ${districtStr ? `<div style="margin-top:6px;font-size:11px;color:#999;">📍 ${districtStr}</div>` : ''}
            </div>
        </div>`;
    }

    async function fetchAgents() {
        const grid = document.getElementById('agentsGrid');
        if (grid) grid.innerHTML = Array(4).fill('<div class="skeleton skeleton-card"></div>').join('');
        
        // Load localStorage-saved agents first
        const localAgents = JSON.parse(localStorage.getItem('gz_agents') || '[]');

        try {
            const response = await fetch(`${API_BASE}/agents/`);
            if (response.ok) {
                const data = await response.json();
                let agents = [];
                if (data.items && Array.isArray(data.items)) agents = data.items;
                else if (Array.isArray(data)) agents = data;

                // Merge API agents with locally-added ones
                const merged = [...localAgents, ...agents];
                window.cachedAgents = merged;
                if (merged.length === 0) {
                    grid.innerHTML = '<div class="no-results" style="grid-column:1/-1; padding:40px; text-align:center;"><h3>Агент олдсонгүй</h3><p style="color:#999; margin-top:8px;">Одоогоор бүртгэлтэй агент байхгүй байна.</p></div>';
                } else {
                    grid.innerHTML = merged.map(a => renderAgentCard(a)).join('');
                }
                return;
            }
        } catch (e) {
            console.warn("Agent API unavailable, showing local agents only.", e);
        }

        // No API - show local agents only
        window.cachedAgents = localAgents;
        if (localAgents.length === 0) {
            grid.innerHTML = '<div class="no-results" style="grid-column:1/-1; padding:40px; text-align:center;"><h3>Агент олдсонгүй</h3><p style="color:#999; margin-top:8px;">Одоогоор бүртгэлтэй агент байхгүй байна.</p></div>';
        } else {
            grid.innerHTML = localAgents.map(a => renderAgentCard(a)).join('');
        }
    }

    window.openAgentProfile = async function(agentId) {
        const modal = document.getElementById('agentProfileModal');
        modal.style.display = 'flex';
        document.getElementById('profileAgentName').innerText = 'Ачааллаж байна...';
        document.getElementById('profileAgentHeader').innerHTML = '<div style="padding:20px;color:#999;">Ачааллаж байна...</div>';
        document.getElementById('profileAgentListings').innerHTML = '';

        // find agent from cache
        let agent = (window.cachedAgents || []).find(a => a.id == agentId);
        if (!agent) agent = FALLBACK_AGENTS.find(a => a.id == agentId) || { id: agentId, name: 'Агент', company: 'RE/MAX', image: 'https://i.pravatar.cc/150?u=agent', rating: '5.0', listings_count: 0, total_sales: 0 };

        // try to get full data from API
        try {
            const r = await fetch(`${API_BASE}/agents/${agentId}`);
            if (r.ok) agent = await r.json();
        } catch(e) {}

        const badgeHtml = agent.badge === 'top' ? '<span style="background:#ffc107;color:#000;font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;">⭐ ТОП АГЕНТ</span>' :
            agent.badge === 'verified' ? '<span style="background:#28a745;color:#fff;font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;">✔ Баталгаажсан</span>' : '';

        document.getElementById('profileAgentName').innerText = agent.name || 'Агент';
        document.getElementById('profileAgentHeader').innerHTML = `
            <div style="width:120px;height:120px;border-radius:50%;background-image:url('${agent.avatar_url||agent.image||'https://i.pravatar.cc/150?u=1'}');background-size:cover;background-position:center;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                    <h1 style="font-size:28px;font-weight:800;">${agent.name||'Агент'}</h1>${badgeHtml}
                </div>
                <p style="color:#666;font-size:16px;margin-bottom:15px;">${agent.company||''}</p>
                <p style="color:#555;font-size:14px;margin-bottom:18px;line-height:1.6;">${agent.bio||''}</p>
                <div style="display:flex;gap:24px;flex-wrap:wrap;">
                    <div style="text-align:center;"><div style="font-size:22px;font-weight:800;color:var(--primary-solid);">${agent.rating||'5.0'}</div><div style="font-size:12px;color:#999;">★ Үнэлгээ</div></div>
                    <div style="text-align:center;"><div style="font-size:22px;font-weight:800;color:var(--primary-solid);">${agent.listings_count||0}</div><div style="font-size:12px;color:#999;">Идэвхтэй зар</div></div>
                    <div style="text-align:center;"><div style="font-size:22px;font-weight:800;color:var(--primary-solid);">${agent.total_sales||0}</div><div style="font-size:12px;color:#999;">Борлуулалт</div></div>
                    <div style="text-align:center;"><div style="font-size:22px;font-weight:800;color:var(--primary-solid);">${agent.years_exp||0}</div><div style="font-size:12px;color:#999;">Жил</div></div>
                </div>
            </div>
        `;

        // listings belonging to this agent
        const agentListings = agent.listings || allProperties.filter(p => p.agent === agent.name);
        const grid = document.getElementById('profileAgentListings');
        if (!agentListings || agentListings.length === 0) {
            grid.innerHTML = '<p style="color:#999;padding:20px 0;">Энэ агентад одоогоор идэвхтэй зар байхгүй байна.</p>';
        } else {
            grid.innerHTML = agentListings.map(p => {
                const priceLabel = p.priceLabel || (p.price ? p.price.toLocaleString() + '₮' : 'Үнэгүй');
                const addr = p.addr || p.address || p.district || 'Улаанбаатар';
                const img = p.img || p.primary_image || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80';
                const tag = p.boost_status === 'active' ? '<div class="card-tag tag-gold">⭐ BOOST</div>' :
                    p.owner_role === 'agent' || p.role === 'agent' ? '<div class="card-tag tag-blue">АГЕНТ</div>' :
                    '<div class="card-tag tag-green">ЭНГИЙН</div>';
                const cardClass = p.boost_status === 'active' ? 'card-gold' : p.owner_role === 'agent' || p.role === 'agent' ? 'card-blue' : 'card-green';
                return `<div class="property-card ${cardClass}" onclick="openDetail(${p.id})">
                    <div class="card-img" style="background-image:url('${img}')">${tag}<div class="card-heart" onclick="event.stopPropagation();">♡</div></div>
                    <div class="card-body">
                        <div class="card-price-row"><span class="card-price">${priceLabel}</span><span class="card-size">${p.area||0}м²</span></div>
                        <div class="card-info">${p.rooms||1} өрөө</div>
                        <div class="card-addr">${addr}</div>
                    </div>
                </div>`;
            }).join('');
        }

        // contact button
        const phone = agent.phone || '';
        document.getElementById('profileAgentHeader').insertAdjacentHTML('afterend',
            `<div style="margin:0 0 30px 0;display:flex;gap:12px;">
                <a href="tel:${phone}" style="background:var(--primary-solid);color:white;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px;">📞 ${phone||'Залгах'}</a>
                <button style="background:white;border:2px solid var(--primary-solid);color:var(--primary-solid);padding:12px 24px;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;">💬 Мессеж</button>
            </div>`);
    }

    window.closeAgentProfile = function() {
        document.getElementById('agentProfileModal').style.display = 'none';
    }

    window.toggleCustomSelect = function(id) {
        const wrap = document.getElementById(id);
        const options = wrap.querySelector('.custom-select-options');
        const isActive = wrap.classList.contains('active');
        
        // Close all others
        document.querySelectorAll('.custom-select-wrap').forEach(el => {
            el.classList.remove('active');
            el.querySelector('.custom-select-options').style.display = 'none';
        });

        if (!isActive) {
            wrap.classList.add('active');
            options.style.display = 'block';
        }
    };

    window.selectOption = function(wrapId, optionEl, hiddenId) {
        const wrap = document.getElementById(wrapId);
        const display = wrap.querySelector('.custom-select-display');
        const hidden = document.getElementById(hiddenId);
        
        display.innerText = optionEl.innerText;
        hidden.value = optionEl.getAttribute('data-value');
        
        wrap.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('selected'));
        optionEl.classList.add('selected');
        
        wrap.classList.remove('active');
        wrap.querySelector('.custom-select-options').style.display = 'none';
    };

    window.selectSortOption = function(wrapId, optionEl) {
        const wrap = document.getElementById(wrapId);
        const display = wrap.querySelector('.custom-select-display');
        const hidden = document.getElementById('sortOrderTop');
        
        display.innerText = optionEl.innerText;
        hidden.value = optionEl.getAttribute('data-value');
        
        wrap.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('selected'));
        optionEl.classList.add('selected');
        
        wrap.classList.remove('active');
        wrap.querySelector('.custom-select-options').style.display = 'none';
        
        applyFilters();
    };

    window.syncPrices = function(type, val) {
        if (type === 'min') {
            document.getElementById('minPrice').value = val;
            document.getElementById('minPriceMain').value = val;
            gridFilters.minPrice = val;
        } else {
            document.getElementById('maxPrice').value = val;
            document.getElementById('maxPriceMain').value = val;
            gridFilters.maxPrice = val;
        }
    };

    window.quickPriceRange = function(min, max) {
        syncPrices('min', min || '');
        syncPrices('max', max || '');
        fetchListings('grid');
    };

    // Close on click outside
    window.addEventListener('click', function(e) {
        if (!e.target.closest('.price-expand-wrap')) {
            const p = document.getElementById('priceExpandMain');
            if (p) p.classList.remove('active');
        }
        if (!e.target.closest('.custom-select-wrap')) {

            document.querySelectorAll('.custom-select-wrap').forEach(el => {
                el.classList.remove('active');
                el.querySelector('.custom-select-options').style.display = 'none';
            });
        }
    });

    window.renderMyProfile = function() {
        const container = document.getElementById('profileContent');
        const userPhone = localStorage.getItem('gz_phone');
        const isAdmin = userPhone === ADMIN_PHONE;

        container.innerHTML = `
            <div style="background:white; padding:32px; border-radius:24px; border:1px solid var(--border); margin-top:20px;">
                <div style="display:flex; align-items:center; gap:20px; margin-bottom:32px;">
                    <div style="width:70px; height:70px; border-radius:50%; background:var(--accent); display:flex; align-items:center; justify-content:center; font-size:32px;">👤</div>
                    <div>
                        <h2 style="font-size:24px; font-weight:800;">Хэрэглэгч</h2>
                        <p style="color:var(--text-muted);">+976 ${userPhone}</p>
                    </div>
                </div>
                
                <div style="display:flex; flex-direction:column; gap:12px;">
                    ${isAdmin ? `
                    <button class="btn-post" style="width:100%; background:var(--bg); color:var(--primary); border:1px solid var(--border);" onclick="switchTab('admin')">
                        🛠 АДМИН ХЯНАЛТ
                    </button>
                    ` : `
                    <div id="profileMenu" style="display:flex; flex-direction:column; gap:12px;">
                        <button class="btn-post" style="width:100%; background:white; color:var(--primary); border:1px solid var(--border); justify-content:flex-start; padding:20px;" onclick="showAgentForm()">
                            <span>👤</span> АГЕНТ
                        </button>
                    </div>

                    <div id="agentRequestForm" style="display:none; background:white; padding:24px; border-radius:24px; border:1px solid var(--border); margin-top:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                            <h4 style="font-size:16px;">Агент бүртгэл</h4>
                            <button onclick="renderMyProfile()" style="background:none; border:none; color:var(--text-muted); font-size:12px; cursor:pointer;">БУЦАХ</button>
                        </div>
                        
                        <div style="display:flex; flex-direction:column; gap:16px;">
                            <div style="text-align:center;">
                                <div id="reqPhotoPreview" style="width:80px; height:80px; border-radius:50%; background:var(--bg); margin:0 auto 10px; display:flex; align-items:center; justify-content:center; border:1px dashed var(--accent); cursor:pointer;" onclick="document.getElementById('agentPhotoInput').click()">
                                    <span style="font-size:24px;">📸</span>
                                </div>
                                <input type="file" id="agentPhotoInput" style="display:none;" onchange="handleAgentPhoto(event)">
                                <p style="font-size:11px; color:var(--text-muted);">Профайл зураг</p>
                            </div>

                            <input type="text" id="reqName" placeholder="Бүтэн нэр" style="width:100%; padding:14px; border-radius:12px; border:1px solid var(--border);">
                            <input type="text" id="reqCompany" placeholder="Компани (Жишээ: RE/MAX)" style="width:100%; padding:14px; border-radius:12px; border:1px solid var(--border);">
                            <input type="text" id="reqAddress" placeholder="Хаяг (Дүүрэг, хороо)" style="width:100%; padding:14px; border-radius:12px; border:1px solid var(--border);">
                            <input type="text" id="reqPhone" value="${userPhone}" placeholder="Утасны дугаар" style="width:100%; padding:14px; border-radius:12px; border:1px solid var(--border);">
                            <textarea id="reqBio" placeholder="Товч намтар..." style="width:100%; padding:14px; border-radius:12px; border:1px solid var(--border); height:80px;"></textarea>
                            
                            <button class="btn-post" style="width:100%;" onclick="submitAgentRequest()">ХҮСЭЛТ ИЛГЭЭХ</button>
                        </div>
                    </div>
                    `}
                    <button class="btn-outline" style="width:100%;" onclick="logout()">
                        🚪 ГАРАХ
                    </button>
                </div>
            </div>
        `;
    };

    let currentTab = 'home';

    window.switchTab = function(tab) {
        currentTab = tab;
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        const activeTab = document.getElementById(`tab-${tab}`);
        if (activeTab) activeTab.classList.add('active');

        document.querySelectorAll('.view-pane').forEach(pane => pane.classList.remove('active'));
        const activePane = document.getElementById(`view${tab.charAt(0).toUpperCase() + tab.slice(1)}`);
        if (activePane) activePane.classList.add('active');

        if (tab === 'home') {
            if (heroMap) setTimeout(() => heroMap.invalidateSize(), 300);
            fetchListings('map');
        } else if (tab === 'listings') {
            fetchListings('grid');
        } else if (tab === 'agents') {
            fetchAgents();
        } else if (tab === 'profile') {
            if (!isLoggedIn) showLogin();
            else renderMyProfile();
        } else if (tab === 'admin') {
            const userPhone = localStorage.getItem('gz_phone');
            if (userPhone === ADMIN_PHONE) renderAdminDashboard();
            else { showToast('Танд хандах эрх байхгүй!'); switchTab('home'); }
        }
    };

    window.renderAdminDashboard = function() {
        const q = (document.getElementById('adminSearchInput')?.value || '').toLowerCase();
        
        // Combine all listings directly to ignore any homepage filters
        const localListings = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
        const firebaseIds = new Set(allFirebaseListings.map(p => p.id));
        const uniqueLocalListings = localListings.filter(p => !firebaseIds.has(p.id));
        const allListings = [...uniqueLocalListings, ...allFirebaseListings];
        
        const filtered = allListings.filter(p => (p.title || '').toLowerCase().includes(q));

        document.getElementById('statTotalListings').innerText = allListings.length;
        document.getElementById('statBoosted').innerText = allListings.filter(p => p.boost).length;
        const localAgents = JSON.parse(localStorage.getItem('gz_agents') || '[]');
        const totalAgents = window.cachedAgents && window.cachedAgents.length > 0 ? window.cachedAgents.length : localAgents.length;
        document.getElementById('statAgents').innerText = totalAgents;

        // Dynamic user stats based on unique phones in all listings
        const uniquePhones = new Set();
        allListings.forEach(p => {
            if (p.phone && String(p.phone).trim() !== '' && p.phone !== '99XX-XXXX') {
                uniquePhones.add(String(p.phone).trim());
            }
        });
        const totalUsersCount = uniquePhones.size > 0 ? uniquePhones.size : 1;
        document.getElementById('statTotalUsers').innerText = totalUsersCount.toLocaleString();
        document.getElementById('statDailyLogins').innerText = Math.max(1, Math.floor(totalUsersCount * 0.15));

        // Render Agent Requests
        const reqs = JSON.parse(localStorage.getItem('gz_agent_requests') || '[]');
        const badge = document.getElementById('requestBadge');
        if (badge) {
            badge.innerText = reqs.length;
            badge.style.display = reqs.length > 0 ? 'block' : 'none';
        }
        
        const reqContainer = document.getElementById('adminRequestsTable');
        if (reqContainer) {
            reqContainer.innerHTML = reqs.length === 0 
                ? '<p style="color:#999; font-size:13px; padding:10px;">Одоогоор хүсэлт байхгүй байна.</p>' 
                : reqs.map(r => `
                <div style="background:white; padding:16px; border-radius:16px; border:1px solid var(--border); display:flex; align-items:center; gap:15px; margin-bottom:10px;">
                    <div style="width:44px; height:44px; border-radius:50%; background:url('https://i.pravatar.cc/100?u=${r.name}') center/cover; flex-shrink:0;"></div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:14px; color:var(--primary);">${r.name}</div>
                        <div style="font-size:12px; color:var(--text-muted);">${r.company || 'Компани тодорхойгүй'} • ${r.phone}</div>
                        ${r.bio ? `<div style="font-size:11px; color:#999; margin-top:3px;">${r.bio}</div>` : ''}
                    </div>
                    <div style="display:flex; gap:8px; flex-shrink:0;">
                        <button style="background:var(--primary); color:white; border:none; padding:8px 14px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer;" onclick="approveAgent('${r.id}')">ЗӨВШӨӨРӨХ</button>
                        <button style="background:#fff5f5; color:#ff4757; border:none; padding:8px 14px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer;" onclick="rejectRequest('${r.id}')">ТАТГАЛЗАХ</button>
                    </div>
                </div>
            `).join('');
        }

        // Render Agent Management
        const agentContainer = document.getElementById('adminAgentsTable');
        if (agentContainer) {
            agentContainer.innerHTML = localAgents.length === 0
                ? '<p style="color:#999; font-size:13px; padding:10px;">Одоогоор агент байхгүй байна.</p>'
                : localAgents.map(a => `
                <div style="background:white; padding:14px 16px; border-radius:16px; border:1px solid var(--border); display:flex; align-items:center; gap:14px; margin-bottom:10px;">
                    <div style="width:44px; height:44px; border-radius:50%; background:url('${a.image || 'https://i.pravatar.cc/100?u=' + a.name}') center/cover; flex-shrink:0;"></div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:14px; color:var(--primary);">${a.name}</div>
                        <div style="font-size:12px; color:var(--text-muted);">${a.company || ''} • ${a.phone || ''}</div>
                    </div>
                    <button style="background:#fff5f5; color:#ff4757; border:none; padding:8px 14px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer;" onclick="deleteAgent(${a.id})">УСТГАХ</button>
                </div>
            `).join('');
        }

        // Render Listings Management
        const container = document.getElementById('adminListingsTable');
        if (container) {
            container.innerHTML = filtered.length === 0
                ? '<p style="color:#999; font-size:13px; padding:10px;">Зар байхгүй байна.</p>'
                : filtered.slice(0, 50).map(p => `
                <div style="background:white; padding:16px; border-radius:16px; border:1px solid var(--border); display:flex; align-items:center; gap:15px; margin-bottom:10px;">
                    <div style="width:50px; height:50px; border-radius:10px; background:url('${p.img}') center/cover; flex-shrink:0;"></div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:14px; color:var(--primary);">${p.title}</div>
                        <div style="font-size:12px; color:var(--text-muted);">${p.priceLabel} • ${p.addr}</div>
                        <div style="font-size:11px; color:#999; margin-top:2px;">${p.phone || ''}</div>
                    </div>
                    <div style="display:flex; gap:8px; flex-shrink:0;">
                        <button style="background:${p.boost ? '#f59e0b' : 'var(--bg)'}; color:${p.boost ? 'white' : 'var(--primary)'}; border:none; padding:8px 12px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer;" onclick="toggleBoost('${p.id}')">
                            ${p.boost ? 'UNBOOST' : 'BOOST'}
                        </button>
                        <button style="background:#fff5f5; color:#ff4757; border:none; padding:8px 12px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer;" onclick="deleteListing('${p.id}')">УСТГАХ</button>
                    </div>
                </div>
            `).join('');
        }
    };

    window.toggleBoost = async function(id) {
        const stringId = String(id);
        if (stringId.startsWith('local_')) {
            const listings = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
            const idx = listings.findIndex(p => String(p.id) === stringId);
            if (idx !== -1) {
                listings[idx].boost = !listings[idx].boost;
                localStorage.setItem('gz_local_listings', JSON.stringify(listings));
                showToast(listings[idx].boost ? 'Зар BOOST хийгдлээ!' : 'BOOST цуцлагдлаа.');
            }
            renderAdminDashboard();
        } else {
            const p = allFirebaseListings.find(x => String(x.id) === stringId);
            if (p) {
                try {
                    await db.collection("listings").doc(stringId).update({ 
                        boost_status: p.boost ? 'inactive' : 'active', 
                        boost: !p.boost 
                    });
                    showToast(!p.boost ? 'Зар BOOST хийгдлээ!' : 'BOOST цуцлагдлаа.');
                    p.boost = !p.boost;
                    p.boost_status = p.boost ? 'active' : 'inactive';
                    renderAdminDashboard();
                } catch (e) {
                    showToast('Firebase алдаа гарлаа: ' + e.message, true);
                }
            } else {
                showToast('Зар олдсонгүй (Firebase ID mismatch)');
            }
        }
    };

    window.deleteListing = async function(id) {
        if (!confirm('Энэ зарыг устгахдаа итгэлтэй байна уу?')) return;
        const stringId = String(id);
        if (stringId.startsWith('local_')) {
            const listings = JSON.parse(localStorage.getItem('gz_local_listings') || '[]');
            const filtered = listings.filter(p => String(p.id) !== stringId);
            localStorage.setItem('gz_local_listings', JSON.stringify(filtered));
            gridProperties = gridProperties.filter(p => String(p.id) !== stringId);
            mapProperties = mapProperties.filter(p => String(p.id) !== stringId);
            allProperties = allProperties.filter(p => String(p.id) !== stringId);
            showToast('Зар устгагдлаа.');
            renderAdminDashboard();
            renderListings(gridProperties, 'grid');
            renderListings(mapProperties, 'map');
        } else {
            try {
                await db.collection("listings").doc(stringId).delete();
                showToast('Зар устгагдлаа.');
                // Optimistic local update
                allFirebaseListings = allFirebaseListings.filter(x => String(x.id) !== stringId);
                renderAdminDashboard();
                fetchListings('grid');
                fetchListings('map');
            } catch (e) {
                showToast('Firebase алдаа: ' + e.message, true);
            }
        }
    };

    window.deleteAgent = function(id) {
        if (!confirm('Энэ агентыг устгах уу?')) return;
        let agents = JSON.parse(localStorage.getItem('gz_agents') || '[]');
        agents = agents.filter(a => a.id != id);
        localStorage.setItem('gz_agents', JSON.stringify(agents));
        if (window.cachedAgents) window.cachedAgents = window.cachedAgents.filter(a => a.id != id);
        showToast('Агент устгагдлаа.');
        renderAdminDashboard();
    };

    window.createNewAgent = function() {
        const name = document.getElementById('newAgentName').value;
        const company = document.getElementById('newAgentCompany').value;
        const phone = document.getElementById('newAgentPhone').value;
        const bio = document.getElementById('newAgentBio').value;

        if (!name || !phone) { showToast('Нэр болон дугаар заавал хэрэгтэй!'); return; }
        addAgentToList({ name, company, phone, bio });
        
        // Clear form
        document.getElementById('newAgentName').value = '';
        document.getElementById('newAgentCompany').value = '';
        document.getElementById('newAgentPhone').value = '';
        document.getElementById('newAgentBio').value = '';
        renderAdminDashboard();
    };

    function addAgentToList(data) {
        const newAgent = {
            id: Date.now(),
            name: data.name,
            company: data.company || 'Бие даасан агент',
            phone: data.phone,
            bio: data.bio,
            listings_count: 0,
            rating: '5.0',
            image: data.image || `https://i.pravatar.cc/150?u=${encodeURIComponent(data.name)}`,
            badge: 'new'
        };
        // Save to localStorage
        const agents = JSON.parse(localStorage.getItem('gz_agents') || '[]');
        agents.unshift(newAgent);
        localStorage.setItem('gz_agents', JSON.stringify(agents));
        if (!window.cachedAgents) window.cachedAgents = [];
        window.cachedAgents.unshift(newAgent);
        showToast(`Агент ${data.name} амжилттай нэмэгдлээ!`);
    }

    window.submitAgentRequest = function() {
        const name = document.getElementById('reqName').value;
        const company = document.getElementById('reqCompany').value;
        const bio = document.getElementById('reqBio').value;
        const phone = localStorage.getItem('gz_phone');

        if (!name) { showToast('Нэрээ оруулна уу!'); return; }

        const reqs = JSON.parse(localStorage.getItem('gz_agent_requests') || '[]');
        reqs.push({ id: Date.now().toString(), name, company, bio, phone });
        localStorage.setItem('gz_agent_requests', JSON.stringify(reqs));

        document.getElementById('agentRequestForm').innerHTML = `
            <div style="text-align:center; padding:20px;">
                <div style="font-size:40px; margin-bottom:15px;">📩</div>
                <p style="font-size:16px; font-weight:800; color:var(--primary); margin-bottom:8px;">Хүсэлт илгээгдлээ!</p>
                <p style="font-size:12px; color:var(--text-muted); line-height:1.6;">Админ таны мэдээллийг шалгаж байна. Тун удахгүй хариу өгөх болно.</p>
                <button class="btn-outline" style="width:100%; margin-top:24px; padding:12px;" onclick="renderMyProfile()">ОЙЛГОЛОО</button>
            </div>
        `;
        showToast('Агент болох хүсэлт илгээгдлээ.');
    };

    window.showAgentForm = function() {
        document.getElementById('profileMenu').style.display = 'none';
        document.getElementById('agentRequestForm').style.display = 'block';
    };

    let agentPhotoBase64 = null;
    window.handleAgentPhoto = function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            agentPhotoBase64 = ev.target.result;
            const preview = document.getElementById('reqPhotoPreview');
            preview.innerHTML = '';
            preview.style.background = `url('${agentPhotoBase64}') center/cover`;
            preview.style.border = '2px solid white';
            preview.style.boxShadow = 'var(--shadow-sm)';
        };
        reader.readAsDataURL(file);
    };

    window.approveAgent = function(reqId) {
        let reqs = JSON.parse(localStorage.getItem('gz_agent_requests') || '[]');
        const req = reqs.find(r => r.id === reqId);
        if (req) {
            const agentData = {
                name: req.name,
                company: req.company,
                phone: req.phone,
                bio: req.bio,
                image: req.image || `https://i.pravatar.cc/150?u=${req.name}`,
                districts: [req.address || 'Улаанбаатар']
            };
            addAgentToList(agentData);
            reqs = reqs.filter(r => r.id !== reqId);
            localStorage.setItem('gz_agent_requests', JSON.stringify(reqs));
            renderAdminDashboard();
        }
    };

    window.rejectRequest = function(reqId) {
        if (confirm('Энэ хүсэлтийг цуцлах уу?')) {
            let reqs = JSON.parse(localStorage.getItem('gz_agent_requests') || '[]');
            reqs = reqs.filter(r => r.id !== reqId);
            localStorage.setItem('gz_agent_requests', JSON.stringify(reqs));
            renderAdminDashboard();
            showToast('Хүсэлтийг цуцаллаа.');
        }
    };





    const CATEGORIES = [
        { id: 'all', name: 'Бүх', icon: 'layers' },
        { id: 'land', name: 'Газар', icon: 'map' },
        { id: 'yard_house', name: 'Хашаа байшин', icon: 'fence' },
        { id: 'house', name: 'Хаус', icon: 'home' },
        { id: 'apartment', name: 'Орон сууц', icon: 'building' }
    ];

    function renderCategories() {
        const bars = [
            { el: document.getElementById('mapCatBar'), type: 'map' },
            { el: document.getElementById('fullCatBar'), type: 'grid' }
        ];

        bars.forEach(bar => {
            if (!bar.el) return;
            const currentCat = bar.type === 'map' ? mapCategory : gridCategory;
            bar.el.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:12px; width:100%;">
                    <div style="display:flex; align-items:center; gap:8px; overflow-x:auto; padding:4px 0; scrollbar-width:none;">
                        ${CATEGORIES.map(c => `
                            <div class="cat-item ${c.id === currentCat ? 'active' : ''}" data-cat="${c.id}" onclick="selectCategory('${bar.type}', '${c.id}')" style="flex-shrink:0;">
                                <i data-lucide="${c.icon}"></i>
                                <span>${c.name}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        if (window.lucide) lucide.createIcons();
    }

    window.selectCategory = function(type, catId) {
        if (type === 'map') mapCategory = catId;
        else gridCategory = catId;
        renderCategories();
        fetchListings(type);
    };

    window.applyFilters = function() {
        fetchListings(currentTab === 'home' ? 'map' : 'grid');
    };

    window.onload = () => {
        initMap();
        renderCategories();
        fetchListings('map');
        fetchListings('grid');
        fetchAgents();
        checkAuth();
        setTimeout(() => lucide.createIcons(), 500);
    };


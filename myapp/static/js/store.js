(() => {
    const cartStorageKey = "forma-studio-cart";
    const cartCount = document.querySelector("[data-cart-count]");
    const cartButton = document.querySelector("[data-cart-open]");
    const cartDrawer = document.querySelector("[data-cart-drawer]");
    const cartOverlay = document.querySelector("[data-cart-overlay]");
    const cartItems = document.querySelector("[data-cart-items]");
    const cartEmpty = document.querySelector("[data-cart-empty]");
    const cartSubtotal = document.querySelector("[data-cart-subtotal]");
    const toast = document.querySelector("[data-toast]");
    let toastTimer;
    let lastFocusedElement;

    function showToast(message) {
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("is-visible");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2600);
    }

    function readCart() {
        try {
            const storedCart = JSON.parse(window.localStorage.getItem(cartStorageKey) || "[]");
            if (!Array.isArray(storedCart)) throw new TypeError("Saved cart must be a list.");
            return storedCart.filter((item) =>
                item &&
                typeof item.id === "string" &&
                typeof item.name === "string" &&
                Number.isFinite(item.price) &&
                Number.isInteger(item.quantity) &&
                item.quantity > 0
            );
        } catch (error) {
            console.error("Could not read the saved shopping bag.", error);
            showToast("Your saved bag couldn't be loaded. Start a fresh one.");
            return [];
        }
    }

    let cart = readCart();

    function saveCart() {
        try {
            window.localStorage.setItem(cartStorageKey, JSON.stringify(cart));
            return true;
        } catch (error) {
            console.error("Could not save the shopping bag.", error);
            showToast("Your bag couldn't be saved on this device.");
            return false;
        }
    }

    function formatPrice(price) {
        return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(price);
    }

    function updateCart() {
        if (!cartCount || !cartItems || !cartSubtotal) return;

        const totalItems = cart.reduce((total, item) => total + item.quantity, 0);
        const subtotal = cart.reduce((total, item) => total + item.price * item.quantity, 0);
        cartCount.textContent = String(totalItems);
        cartButton?.setAttribute("aria-label", `Open shopping bag, ${totalItems} ${totalItems === 1 ? "item" : "items"}`);

        const titleCount = document.querySelector("[data-cart-title-count]");
        if (titleCount) titleCount.textContent = `(${totalItems})`;
        cartSubtotal.textContent = formatPrice(subtotal);
        cartItems.replaceChildren();

        cart.forEach((item) => {
            const line = document.createElement("article");
            line.className = "cart-line";

            const image = document.createElement("img");
            image.className = "cart-line__image";
            image.src = item.image;
            image.alt = "";

            const details = document.createElement("div");
            details.className = "cart-line__info";
            const name = document.createElement("strong");
            name.textContent = item.name;
            const price = document.createElement("span");
            price.textContent = formatPrice(item.price);

            const quantity = document.createElement("div");
            quantity.className = "quantity-control";
            quantity.setAttribute("aria-label", `Quantity for ${item.name}`);
            const decrease = document.createElement("button");
            decrease.type = "button";
            decrease.setAttribute("aria-label", `Remove one ${item.name}`);
            decrease.dataset.quantityAction = "decrease";
            decrease.dataset.id = item.id;
            decrease.textContent = "−";
            const count = document.createElement("span");
            count.textContent = String(item.quantity);
            const increase = document.createElement("button");
            increase.type = "button";
            increase.setAttribute("aria-label", `Add one ${item.name}`);
            increase.dataset.quantityAction = "increase";
            increase.dataset.id = item.id;
            increase.textContent = "+";
            quantity.append(decrease, count, increase);
            details.append(name, price, quantity);

            const lineTotal = document.createElement("span");
            lineTotal.className = "cart-line__price";
            lineTotal.textContent = formatPrice(item.price * item.quantity);

            line.append(image, details, lineTotal);
            cartItems.append(line);
        });

        const isEmpty = cart.length === 0;
        cartEmpty?.classList.toggle("is-visible", isEmpty);
        cartItems.hidden = isEmpty;
    }

    function openCart() {
        if (!cartDrawer || !cartOverlay) return;
        lastFocusedElement = document.activeElement;
        cartDrawer.inert = false;
        cartDrawer.setAttribute("aria-hidden", "false");
        cartOverlay.hidden = false;
        document.body.classList.add("cart-open");
        requestAnimationFrame(() => {
            cartDrawer.classList.add("is-open");
            cartOverlay.classList.add("is-visible");
        });
        cartDrawer.querySelector("[data-cart-close]")?.focus();
    }

    function closeCart() {
        if (!cartDrawer || !cartOverlay) return;
        cartDrawer.classList.remove("is-open");
        cartOverlay.classList.remove("is-visible");
        cartDrawer.setAttribute("aria-hidden", "true");
        cartDrawer.inert = true;
        document.body.classList.remove("cart-open");
        window.setTimeout(() => {
            if (!cartDrawer.classList.contains("is-open")) cartOverlay.hidden = true;
        }, 300);
        if (lastFocusedElement instanceof HTMLElement) lastFocusedElement.focus();
    }

    cartButton?.addEventListener("click", openCart);
    document.querySelector("[data-cart-close]")?.addEventListener("click", closeCart);
    cartOverlay?.addEventListener("click", closeCart);
    document.querySelector("[data-cart-shop]")?.addEventListener("click", closeCart);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && cartDrawer?.classList.contains("is-open")) closeCart();
    });

    document.addEventListener("click", (event) => {
        const addButton = event.target.closest("[data-add-to-cart]");
        if (addButton) {
            const card = addButton.closest("[data-product-card]");
            const product = {
                id: addButton.dataset.id,
                name: addButton.dataset.name,
                price: Number(addButton.dataset.price),
                image: card?.querySelector("img")?.src || "",
            };
            if (!product.id || !product.name || !Number.isFinite(product.price)) {
                showToast("This item couldn't be added. Please try again.");
                return;
            }
            const existing = cart.find((item) => item.id === product.id);
            if (existing) existing.quantity += 1;
            else cart.push({ ...product, quantity: 1 });
            saveCart();
            updateCart();
            showToast(`${product.name} added to your bag.`);
            return;
        }

        const quantityButton = event.target.closest("[data-quantity-action]");
        if (!quantityButton) return;
        const item = cart.find((entry) => entry.id === quantityButton.dataset.id);
        if (!item) return;
        if (quantityButton.dataset.quantityAction === "increase") item.quantity += 1;
        else item.quantity -= 1;
        cart = cart.filter((entry) => entry.quantity > 0);
        saveCart();
        updateCart();
    });

    const carousel = document.querySelector("[data-carousel]");
    if (carousel) {
        const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
        const countLabel = carousel.querySelector("[data-carousel-count]");
        const captionLabel = carousel.querySelector("[data-carousel-caption]");
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
        let currentSlide = 0;
        let temporarilyPaused = false;
        let carouselTimer;

        function showSlide(index) {
            currentSlide = (index + slides.length) % slides.length;
            slides.forEach((slide, slideIndex) => {
                const isActive = slideIndex === currentSlide;
                slide.classList.toggle("is-active", isActive);
                slide.setAttribute("aria-hidden", String(!isActive));
                const image = slide.querySelector("img");
                if (isActive && image) image.loading = "eager";
            });
            if (countLabel) countLabel.textContent = `${String(currentSlide + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
            if (captionLabel) captionLabel.textContent = slides[currentSlide].dataset.caption || "";
        }

        function updateCarouselTimer() {
            window.clearInterval(carouselTimer);
            const shouldPlay = !reducedMotion.matches && !temporarilyPaused && !document.hidden;
            if (shouldPlay) carouselTimer = window.setInterval(() => showSlide(currentSlide + 1), 5000);
        }

        carousel.addEventListener("mouseenter", () => {
            temporarilyPaused = true;
            updateCarouselTimer();
        });
        carousel.addEventListener("mouseleave", () => {
            temporarilyPaused = false;
            updateCarouselTimer();
        });
        carousel.addEventListener("focusin", () => {
            temporarilyPaused = true;
            updateCarouselTimer();
        });
        carousel.addEventListener("focusout", (event) => {
            if (!carousel.contains(event.relatedTarget)) {
                temporarilyPaused = false;
                updateCarouselTimer();
            }
        });
        document.addEventListener("visibilitychange", updateCarouselTimer);
        reducedMotion.addEventListener("change", updateCarouselTimer);
        showSlide(0);
        updateCarouselTimer();
    }

    const filmPlayer = document.querySelector("[data-film-player]");
    if (filmPlayer) {
        const canvas = filmPlayer.querySelector("[data-film-canvas]");
        const context = canvas?.getContext("2d");
        const frames = Array.from(filmPlayer.querySelectorAll("[data-film-frame]"));
        const status = filmPlayer.querySelector("[data-film-status]");
        const duration = 16;
        const secondsPerFrame = duration / frames.length;
        let startedAt;
        let animationFrame;

        function drawImage(image, opacity, zoom) {
            if (!context || !canvas || !image.naturalWidth) return;
            const width = canvas.width;
            const height = canvas.height;
            const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight) * zoom;
            const drawWidth = image.naturalWidth * scale;
            const drawHeight = image.naturalHeight * scale;
            context.globalAlpha = opacity;
            context.drawImage(image, (width - drawWidth) / 2, (height - drawHeight) / 2, drawWidth, drawHeight);
        }

        function renderFilm(timestamp) {
            if (!context || !canvas || !frames.length) return;
            const currentTime = Number.isFinite(timestamp) ? timestamp : performance.now();
            const elapsed = ((currentTime - startedAt) / 1000) % duration;
            const frameIndex = Math.max(0, Math.min(Math.floor(elapsed / secondsPerFrame), frames.length - 1));
            const currentFrame = frames[frameIndex];
            if (!currentFrame) {
                console.error("The current studio film frame is unavailable.");
                if (status) status.textContent = "The studio film could not be played.";
                return;
            }
            const frameProgress = (elapsed % secondsPerFrame) / secondsPerFrame;
            const transition = Math.max(0, Math.min(1, (frameProgress - 0.78) / 0.22));

            context.clearRect(0, 0, canvas.width, canvas.height);
            drawImage(currentFrame, 1, 1.025);
            if (transition > 0 && frameIndex < frames.length - 1) {
                drawImage(frames[frameIndex + 1], transition, 1.025);
            } else if (transition > 0) {
                drawImage(frames[0], transition, 1.025);
            }
            context.globalAlpha = 1;
            animationFrame = window.requestAnimationFrame(renderFilm);
        }

        if (context && canvas && frames.length) {
            window.addEventListener("pagehide", () => window.cancelAnimationFrame(animationFrame), { once: true });
            const frameLoads = frames.map((frame) => {
                if (frame.complete) {
                    return frame.naturalWidth
                        ? Promise.resolve()
                        : Promise.reject(new Error(`Film frame failed to load: ${frame.currentSrc}`));
                }
                return new Promise((resolve, reject) => {
                    frame.addEventListener("load", resolve, { once: true });
                    frame.addEventListener("error", () => reject(new Error(`Film frame failed to load: ${frame.currentSrc}`)), { once: true });
                });
            });

            Promise.all(frameLoads).then(() => {
                drawImage(frames[0], 1, 1);
                context.globalAlpha = 1;
                filmPlayer.classList.add("is-ready");
                if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                    if (status) status.textContent = "The Forma Studio lookbook film is ready.";
                    return;
                }
                startedAt = performance.now();
                if (status) status.textContent = "The Forma Studio lookbook film is playing.";
                animationFrame = window.requestAnimationFrame(renderFilm);
            }).catch((error) => {
                console.error("Could not load the studio film frames.", error);
                if (status) status.textContent = "The studio film could not be loaded.";
            });
        } else {
            console.error("The studio film player is missing its canvas or frames.");
            if (status) status.textContent = "The studio film is unavailable.";
        }
    }

    const checkoutRoot = document.querySelector("[data-checkout-root]");
    if (checkoutRoot) {
        const checkoutForm = checkoutRoot.querySelector("[data-checkout-form]");
        const checkoutItems = checkoutRoot.querySelector("[data-checkout-items]");
        const checkoutEmpty = checkoutRoot.querySelector("[data-checkout-empty]");
        const checkoutTotal = checkoutRoot.querySelector("[data-checkout-total]");
        const checkoutStatus = checkoutRoot.querySelector("[data-checkout-status]");
        const paypalButtons = checkoutRoot.querySelector("[data-paypal-buttons]");
        const csrfToken = checkoutForm?.querySelector("[name=csrfmiddlewaretoken]")?.value;
        const productData = document.querySelector("#checkout-products");
        const products = new Map(JSON.parse(productData?.textContent || "[]").map((product) => [
            product.id,
            {
                name: product.name,
                price: Number(product.price),
                image: `${checkoutRoot.dataset.staticPrefix}${product.image}`,
            },
        ]));
        let checkoutCart = [];

        function readCheckoutCart() {
            try {
                const savedCart = JSON.parse(window.localStorage.getItem(cartStorageKey) || "[]");
                if (!Array.isArray(savedCart)) throw new TypeError("Saved cart must be a list.");
                return savedCart.filter((item) =>
                    item &&
                    typeof item.id === "string" &&
                    Number.isInteger(item.quantity) &&
                    item.quantity > 0 &&
                    products.has(item.id)
                ).map((item) => ({
                    id: item.id,
                    quantity: item.quantity,
                    ...products.get(item.id),
                }));
            } catch (error) {
                console.error("Could not read the shopping bag for checkout.", error);
                if (checkoutStatus) checkoutStatus.textContent = "Your bag couldn't be loaded. Please return to the shop and try again.";
                return [];
            }
        }

        function renderCheckoutSummary() {
            if (!checkoutItems || !checkoutTotal || !checkoutEmpty) return;
            checkoutItems.replaceChildren();
            const total = checkoutCart.reduce((sum, item) => sum + item.price * item.quantity, 0);

            checkoutCart.forEach((item) => {
                const row = document.createElement("article");
                row.className = "checkout-line";
                const image = document.createElement("img");
                image.src = item.image;
                image.alt = "";
                const name = document.createElement("span");
                name.textContent = `${item.name} × ${item.quantity}`;
                const price = document.createElement("strong");
                price.textContent = formatPrice(item.price * item.quantity);
                row.append(image, name, price);
                checkoutItems.append(row);
            });

            checkoutTotal.textContent = formatPrice(total);
            checkoutEmpty.hidden = checkoutCart.length > 0;
        }

        function showCheckoutError(error) {
            if (checkoutStatus) checkoutStatus.textContent = error || "Checkout couldn't be completed. Please try again.";
        }

        checkoutCart = readCheckoutCart();
        renderCheckoutSummary();

        if (paypalButtons && checkoutForm && csrfToken && window.paypal) {
            window.paypal.Buttons({
                onClick: (data, actions) => {
                    if (!checkoutForm.reportValidity()) return actions.reject();
                    if (!checkoutCart.length) {
                        showCheckoutError("Your bag is empty. Add a piece before checking out.");
                        return actions.reject();
                    }
                    return actions.resolve();
                },
                createOrder: () => {
                    const customer = new FormData(checkoutForm);
                    return window.fetch(checkoutRoot.dataset.createOrderUrl, {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfToken,
                        },
                        body: JSON.stringify({
                            name: customer.get("name"),
                            email: customer.get("email"),
                            items: checkoutCart.map(({ id, quantity }) => ({ id, quantity })),
                        }),
                    }).then(async (response) => {
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error || "PayPal couldn't start your payment.");
                        return result.orderID;
                    }).catch((error) => {
                        console.error("Could not create the PayPal order.", error);
                        showCheckoutError(error.message);
                        throw error;
                    });
                },
                onApprove: (data) => window.fetch(checkoutRoot.dataset.captureOrderUrl, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ orderID: data.orderID }),
                }).then(async (response) => {
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || "PayPal couldn't verify your payment.");
                    try {
                        window.localStorage.removeItem(cartStorageKey);
                    } catch (error) {
                        console.error("The paid order's shopping bag could not be cleared.", error);
                    }
                    checkoutCart = [];
                    renderCheckoutSummary();
                    if (cartCount) cartCount.textContent = "0";
                    if (checkoutStatus) checkoutStatus.textContent = "Payment complete. Thank you for choosing Forma Studio.";
                }).catch((error) => {
                    console.error("Could not capture the PayPal payment.", error);
                    showCheckoutError(error.message);
                }),
                onError: (error) => {
                    console.error("PayPal checkout encountered an error.", error);
                    showCheckoutError("PayPal couldn't complete your payment. Please try again.");
                },
            }).render(paypalButtons).catch((error) => {
                console.error("Could not load the PayPal checkout buttons.", error);
                showCheckoutError("PayPal couldn't load. Please refresh the page or try again later.");
            });
        } else if (paypalButtons) {
            console.error("PayPal checkout is configured on the server but the PayPal SDK did not load.");
            showCheckoutError("PayPal couldn't load. Please refresh the page or try again later.");
        }
    }

    const productGrid = document.querySelector("[data-product-grid]");
    if (productGrid) {
        const cards = Array.from(productGrid.querySelectorAll("[data-product-card]"));
        const filters = Array.from(document.querySelectorAll("[data-filter]"));
        const searchInput = document.querySelector("[data-product-search]");
        const sortSelect = document.querySelector("[data-product-sort]");
        const resultsCount = document.querySelector("[data-results-count]");
        const emptyResults = document.querySelector("[data-empty-results]");
        let activeCategory = "all";

        function applyCatalogControls() {
            const query = searchInput?.value.trim().toLocaleLowerCase() || "";
            let visibleCount = 0;

            cards.forEach((card) => {
                const matchesCategory = activeCategory === "all" || card.dataset.category === activeCategory;
                const matchesSearch = (card.dataset.search || "").toLocaleLowerCase().includes(query);
                card.hidden = !(matchesCategory && matchesSearch);
                if (!card.hidden) visibleCount += 1;
            });

            if (resultsCount) resultsCount.textContent = `${visibleCount} ${visibleCount === 1 ? "piece" : "pieces"}`;
            if (emptyResults) emptyResults.hidden = visibleCount !== 0;
        }

        filters.forEach((filter) => {
            filter.addEventListener("click", () => {
                activeCategory = filter.dataset.filter || "all";
                filters.forEach((button) => {
                    const isActive = button === filter;
                    button.classList.toggle("is-active", isActive);
                    button.setAttribute("aria-pressed", String(isActive));
                });
                applyCatalogControls();
            });
        });

        searchInput?.addEventListener("input", applyCatalogControls);
        sortSelect?.addEventListener("change", () => {
            const sortedCards = [...cards];
            if (sortSelect.value === "price-low") sortedCards.sort((a, b) => Number(a.dataset.price) - Number(b.dataset.price));
            if (sortSelect.value === "price-high") sortedCards.sort((a, b) => Number(b.dataset.price) - Number(a.dataset.price));
            if (sortSelect.value === "featured") sortedCards.sort((a, b) => cards.indexOf(a) - cards.indexOf(b));
            sortedCards.forEach((card) => productGrid.append(card));
        });

        document.querySelector("[data-clear-filters]")?.addEventListener("click", () => {
            if (searchInput) searchInput.value = "";
            activeCategory = "all";
            filters.forEach((button) => {
                const isActive = button.dataset.filter === "all";
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-pressed", String(isActive));
            });
            applyCatalogControls();
        });

        const requestedCategory = new URLSearchParams(window.location.search).get("category");
        const initialFilter = filters.find((filter) => filter.dataset.filter === requestedCategory);
        if (initialFilter) initialFilter.click();
    }

    updateCart();
})();
